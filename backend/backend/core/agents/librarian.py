"""
Librarian Agent for BiZhen Multi-Agent System.

Role: Retrieve relevant materials (quotes, facts, examples) for essay writing.
Model: DeepSeek V3 (Chat) - for tool calling and creative retrieval

The Librarian implements a tiered retrieval strategy:
- Tier 1: Vector DB Search (Local ChromaDB) - Preferred
- Tier 2: LLM Generation - Fallback/Augmentation when DB results insufficient
- Tier 3: Web Search - Last resort for real-time data

This ensures the system can provide materials even with a sparse database.
"""

import os
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI

from backend.core.state import EssayState
from backend.core.agents.base import (
    get_chat_model,
    load_prompt,
    format_prompt,
    invoke_model,
    publish_sse_event,
)
from backend.config import settings


# Minimum thresholds for tiered retrieval
MIN_MATERIALS_FOR_LLM_AUGMENTATION = 5  # Trigger LLM generation if below this
MIN_MATERIALS_CRITICAL = 3  # Trigger web search if below this (critical shortage)


# Placeholder for ChromaDB client - will be initialized when needed
_chroma_client = None


def get_chroma_collection():
    """
    Get or create ChromaDB collection for materials.

    Returns:
        ChromaDB collection instance or None if unavailable
    """
    global _chroma_client
    try:
        import chromadb
        if _chroma_client is None:
            _chroma_client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
            )
        return _chroma_client.get_or_create_collection("materials_collection")
    except Exception as e:
        print(f"Warning: ChromaDB not available: {e}")
        return None


def search_materials(
    query: str,
    category: Optional[str] = None,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Tier 1: Search materials from vector database.

    Args:
        query: Search query text
        category: Optional category filter (quote/fact/theory/literature)
        top_k: Number of results to return

    Returns:
        List of material dictionaries with content, metadata, and source
    """
    collection = get_chroma_collection()

    if collection is None:
        return []  # Return empty, let other tiers handle it

    try:
        # Build where filter if category specified
        where_filter = {"category": category} if category else None

        results = collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where_filter,
        )

        materials = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                materials.append({
                    "content": doc,
                    "category": metadata.get("category", "unknown"),
                    "author": metadata.get("author", ""),
                    "tags": metadata.get("tags", ""),
                    "source": "vector_db",  # Mark source as local DB
                })

        return materials

    except Exception as e:
        print(f"Warning: ChromaDB query failed: {e}")
        return []


def generate_materials_with_llm(
    model: ChatOpenAI,
    topic: str,
    angle: str,
    thesis: str,
    missing_count: int,
    existing_materials: Dict[str, List[str]],
) -> List[Dict[str, Any]]:
    """
    Tier 2: Generate supplementary materials using the LLM's internal knowledge.

    Args:
        model: The ChatOpenAI model instance (DeepSeek V3)
        topic: Essay topic
        angle: Writing angle
        thesis: Central thesis
        missing_count: Number of additional materials needed
        existing_materials: Already retrieved materials to avoid duplication

    Returns:
        List of generated material dictionaries with source marked as "llm_generated"
    """
    # Build context about what we already have
    existing_content = []
    for cat, items in existing_materials.items():
        existing_content.extend(items)

    existing_str = "\n".join(f"- {item}" for item in existing_content[:10])

    prompt = f"""你是一位博学的学者，精通中外名言警句、历史典故和时事素材。
请根据以下作文主题，生成 {missing_count} 条高质量的写作素材。

【作文主题】{topic}
【立意角度】{angle}
【中心论点】{thesis}

【已有素材（请勿重复）】
{existing_str if existing_str else "暂无"}

【要求】
1. 每条素材必须准确、真实、有据可查
2. 优先提供名人名言、历史事实、经典文学引用
3. 确保素材与主题高度相关
4. 避免过于常见的素材（如"司马迁受刑著史记"）
5. 格式要求：每条素材独占一行，包含出处或来源

请直接输出素材，每行一条，格式如下：
[类型] 内容——出处

示例：
[名言] 路漫漫其修远兮，吾将上下而求索。——屈原《离骚》
[事实] 袁隆平院士毕生致力于杂交水稻研究，让中国人的饭碗牢牢端在自己手中。
[理论] 马克思主义认为，实践是检验真理的唯一标准。
[文学] 长风破浪会有时，直挂云帆济沧海。——李白《行路难》"""

    try:
        response = model.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)

        # Parse generated materials
        generated = []
        lines = content.strip().split("\n")

        category_map = {
            "名言": "quote",
            "事实": "fact",
            "理论": "theory",
            "文学": "literature",
        }

        for line in lines:
            line = line.strip()
            if not line or line.startswith("【") or line.startswith("示例"):
                continue

            # Parse category from [类型] prefix
            category = "quote"  # Default
            for cn_cat, en_cat in category_map.items():
                if f"[{cn_cat}]" in line:
                    category = en_cat
                    line = line.replace(f"[{cn_cat}]", "").strip()
                    break

            if line:
                generated.append({
                    "content": line,
                    "category": category,
                    "author": "",
                    "tags": "",
                    "source": "llm_generated",  # Mark as LLM-generated
                })

        return generated[:missing_count]

    except Exception as e:
        print(f"Warning: LLM material generation failed: {e}")
        return []


def search_web_materials(
    topic: str,
    angle: str,
    count: int = 3,
) -> List[Dict[str, Any]]:
    """
    Tier 3: Search for materials using web search APIs.

    Supports multiple search providers:
    - Tavily (TAVILY_API_KEY)
    - SerpAPI (SERPAPI_API_KEY)
    - DuckDuckGo (no API key required, fallback)

    Args:
        topic: Essay topic
        angle: Writing angle
        count: Number of results to fetch

    Returns:
        List of material dictionaries with source marked as "web_search"
    """
    materials = []
    search_query = f"{topic} {angle} 名言 素材 论据"

    # Try Tavily first (if API key available)
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if tavily_key:
        try:
            from langchain_community.tools.tavily_search import TavilySearchResults
            search_tool = TavilySearchResults(max_results=count)
            results = search_tool.invoke({"query": search_query})

            for result in results:
                if isinstance(result, dict):
                    content = result.get("content", result.get("snippet", ""))
                    if content:
                        materials.append({
                            "content": content[:200],  # Truncate long results
                            "category": "fact",
                            "author": "",
                            "tags": "web",
                            "source": "web_search_tavily",
                            "url": result.get("url", ""),
                        })

            if materials:
                print(f"Tavily search returned {len(materials)} results")
                return materials[:count]

        except Exception as e:
            print(f"Tavily search failed: {e}")

    # Try SerpAPI (if API key available)
    serpapi_key = os.environ.get("SERPAPI_API_KEY")
    if serpapi_key and not materials:
        try:
            from langchain_community.utilities import SerpAPIWrapper
            search = SerpAPIWrapper()
            results = search.results(search_query)

            organic_results = results.get("organic_results", [])
            for result in organic_results[:count]:
                snippet = result.get("snippet", "")
                if snippet:
                    materials.append({
                        "content": snippet[:200],
                        "category": "fact",
                        "author": "",
                        "tags": "web",
                        "source": "web_search_serpapi",
                        "url": result.get("link", ""),
                    })

            if materials:
                print(f"SerpAPI search returned {len(materials)} results")
                return materials[:count]

        except Exception as e:
            print(f"SerpAPI search failed: {e}")

    # Try DuckDuckGo as fallback (no API key required)
    if not materials:
        try:
            from langchain_community.tools import DuckDuckGoSearchRun
            search = DuckDuckGoSearchRun()
            result = search.invoke(search_query)

            if result:
                # DuckDuckGo returns a single string, split into sentences
                sentences = result.split(". ")
                for sentence in sentences[:count]:
                    if len(sentence) > 20:  # Filter out very short fragments
                        materials.append({
                            "content": sentence.strip() + ("." if not sentence.endswith(".") else ""),
                            "category": "fact",
                            "author": "",
                            "tags": "web",
                            "source": "web_search_ddg",
                        })

            if materials:
                print(f"DuckDuckGo search returned {len(materials)} results")
                return materials[:count]

        except Exception as e:
            print(f"DuckDuckGo search failed (this is optional): {e}")

    return materials


def get_fallback_materials(query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Provide hardcoded fallback materials when all other tiers fail.

    These are commonly used Gaokao essay materials that ensure the system
    never returns completely empty results.
    """
    fallback = {
        "quotes": [
            {"content": "路漫漫其修远兮，吾将上下而求索。——屈原《离骚》", "author": "屈原", "tags": ["奋斗", "追求"]},
            {"content": "天行健，君子以自强不息；地势坤，君子以厚德载物。——《周易》", "author": "周易", "tags": ["自强", "品德"]},
            {"content": "博学之，审问之，慎思之，明辨之，笃行之。——《中庸》", "author": "中庸", "tags": ["学习", "实践"]},
            {"content": "知之者不如好之者，好之者不如乐之者。——孔子", "author": "孔子", "tags": ["学习", "兴趣"]},
            {"content": "纸上得来终觉浅，绝知此事要躬行。——陆游", "author": "陆游", "tags": ["实践", "学习"]},
        ],
        "facts": [
            {"content": "袁隆平院士毕生致力于杂交水稻研究，让中国人的饭碗牢牢端在自己手中，被誉为'杂交水稻之父'。", "author": "", "tags": ["奉献", "科学"]},
            {"content": "钟南山院士84岁高龄仍奔赴抗疫一线，展现了医者仁心和科学家的担当。", "author": "", "tags": ["担当", "奉献"]},
            {"content": "中国航天从'东方红一号'到'神舟'系列，再到空间站建设，实现了从无到有的伟大跨越。", "author": "", "tags": ["创新", "奋斗"]},
        ],
        "theories": [
            {"content": "马克思主义认为，实践是检验真理的唯一标准，理论必须与实践相结合。", "author": "马克思", "tags": ["哲学", "实践"]},
            {"content": "习近平总书记指出：'青年兴则国家兴，青年强则国家强。'", "author": "习近平", "tags": ["青年", "担当"]},
        ],
        "literature": [
            {"content": "沉舟侧畔千帆过，病树前头万木春。——刘禹锡《酬乐天扬州初逢席上见赠》", "author": "刘禹锡", "tags": ["乐观", "发展"]},
            {"content": "长风破浪会有时，直挂云帆济沧海。——李白《行路难》", "author": "李白", "tags": ["理想", "奋斗"]},
            {"content": "千淘万漉虽辛苦，吹尽狂沙始到金。——刘禹锡", "author": "刘禹锡", "tags": ["坚持", "奋斗"]},
        ],
    }

    results = []
    if category and category in fallback:
        results = [{
            "content": m["content"],
            "category": category,
            "source": "fallback",
            **m
        } for m in fallback[category]]
    else:
        # Return mixed materials
        for cat, items in fallback.items():
            results.extend([{
                "content": m["content"],
                "category": cat,
                "source": "fallback",
                **m
            } for m in items[:2]])

    return results[:5]


def librarian_node(state: EssayState) -> Dict[str, Any]:
    """
    Librarian agent node - retrieves relevant materials via tiered RAG strategy.

    Implements a 3-tier retrieval strategy:
    1. Vector DB Search (Preferred) - Search ChromaDB for at least 5 items
    2. LLM Generation (Augmentation) - If < 5 items, generate supplementary materials
    3. Web Search (Last Resort) - If < 3 items AND API key available

    Args:
        state: Current graph state with angle and thesis

    Returns:
        State updates with materials dictionary and retrieval metadata

    Edge: librarian -> outliner
    """
    task_id = state.get("task_id")
    topic = state.get("topic", "")
    angle = state.get("angle", "")
    thesis = state.get("thesis", "")

    # Publish start event
    if task_id:
        publish_sse_event(
            task_id=task_id,
            event_type="progress",
            agent="librarian",
            message="正在检索名言警句、事实论据...",
        )

    try:
        # Initialize materials dictionary
        materials = {
            "quotes": [],
            "facts": [],
            "theories": [],
            "literature": [],
        }

        # Track retrieval sources for debugging/analytics
        retrieval_sources = {
            "vector_db": 0,
            "llm_generated": 0,
            "web_search": 0,
            "fallback": 0,
        }

        # Build search query from topic, angle, and thesis
        search_query = f"{topic} {angle} {thesis}"

        # ============================================================
        # TIER 1: Vector Database Search (Preferred)
        # ============================================================
        if task_id:
            publish_sse_event(
                task_id=task_id,
                event_type="progress",
                agent="librarian",

                message="[Tier 1] 正在从本地素材库检索...",
            )

        category_map = {
            "quote": "quotes",
            "fact": "facts",
            "theory": "theories",
            "literature": "literature",
        }

        for db_category, dict_key in category_map.items():
            results = search_materials(search_query, category=db_category, top_k=3)
            for r in results:
                materials[dict_key].append(r["content"])
                retrieval_sources["vector_db"] += 1

        total_from_db = sum(len(v) for v in materials.values())
        print(f"[Tier 1] Vector DB returned {total_from_db} materials")

        # ============================================================
        # TIER 2: LLM Generation (Fallback/Augmentation)
        # ============================================================
        total_materials = sum(len(v) for v in materials.values())

        if total_materials < MIN_MATERIALS_FOR_LLM_AUGMENTATION:
            if task_id:
                publish_sse_event(
                    task_id=task_id,
                    event_type="progress",
                    agent="librarian",
                    message=f"[Tier 2] 本地素材不足({total_materials}条)，正在智能生成补充素材...",
                )

            # Get model for generation
            model = get_chat_model()
            missing_count = MIN_MATERIALS_FOR_LLM_AUGMENTATION - total_materials + 3  # Generate a few extra

            generated = generate_materials_with_llm(
                model=model,
                topic=topic,
                angle=angle,
                thesis=thesis,
                missing_count=missing_count,
                existing_materials=materials,
            )

            # Add generated materials to appropriate categories
            for item in generated:
                cat = item.get("category", "quote")
                dict_key = category_map.get(cat, "quotes")
                materials[dict_key].append(item["content"])
                retrieval_sources["llm_generated"] += 1

            print(f"[Tier 2] LLM generated {len(generated)} additional materials")

        # ============================================================
        # TIER 3: Web Search (Last Resort)
        # ============================================================
        total_materials = sum(len(v) for v in materials.values())

        # Only trigger web search if critically short AND any search API is available
        has_search_api = any([
            os.environ.get("TAVILY_API_KEY"),
            os.environ.get("SERPAPI_API_KEY"),
            True,  # DuckDuckGo doesn't require API key
        ])

        if total_materials < MIN_MATERIALS_CRITICAL and has_search_api:
            if task_id:
                publish_sse_event(
                    task_id=task_id,
                    event_type="progress",
                    agent="librarian",
                    message=f"[Tier 3] 素材严重不足({total_materials}条)，正在联网搜索...",
                )

            web_results = search_web_materials(topic, angle, count=3)

            for item in web_results:
                # Add web results primarily as facts
                materials["facts"].append(item["content"])
                retrieval_sources["web_search"] += 1

            print(f"[Tier 3] Web search returned {len(web_results)} materials")

        # ============================================================
        # FALLBACK: Hardcoded Materials (Emergency)
        # ============================================================
        total_materials = sum(len(v) for v in materials.values())

        if total_materials < MIN_MATERIALS_CRITICAL:
            if task_id:
                publish_sse_event(
                    task_id=task_id,
                    event_type="progress",
                    agent="librarian",
                    message="[Fallback] 使用备用素材库...",
                )

            fallback_items = get_fallback_materials(search_query)
            for item in fallback_items:
                cat = item.get("category", "quote")
                dict_key = category_map.get(cat, "quotes")
                if len(materials[dict_key]) < 3:  # Don't overfill
                    materials[dict_key].append(item["content"])
                    retrieval_sources["fallback"] += 1

            print(f"[Fallback] Added {retrieval_sources['fallback']} emergency materials")

        # ============================================================
        # Publish Completion
        # ============================================================
        total_materials = sum(len(v) for v in materials.values())

        # Build source summary
        source_parts = []
        if retrieval_sources["vector_db"] > 0:
            source_parts.append(f"本地库{retrieval_sources['vector_db']}条")
        if retrieval_sources["llm_generated"] > 0:
            source_parts.append(f"AI生成{retrieval_sources['llm_generated']}条")
        if retrieval_sources["web_search"] > 0:
            source_parts.append(f"网络搜索{retrieval_sources['web_search']}条")
        if retrieval_sources["fallback"] > 0:
            source_parts.append(f"备用{retrieval_sources['fallback']}条")

        source_summary = "、".join(source_parts) if source_parts else "无"

        if task_id:
            publish_sse_event(
                task_id=task_id,
                event_type="progress",
                agent="librarian",
                message=f"素材检索完成，共找到 {total_materials} 条相关素材（来源：{source_summary}）",
                data=materials,
            )

        return {
            "materials": materials,
            "current_agent": "librarian",
            "retrieval_metadata": {
                "total": total_materials,
                "sources": retrieval_sources,
            },
        }

    except Exception as e:
        if task_id:
            publish_sse_event(
                task_id=task_id,
                event_type="error",
                agent="librarian",
                message=f"素材检索失败: {str(e)}",
            )

        # Return fallback materials on error
        fallback_materials = {
            "quotes": [m["content"] for m in get_fallback_materials("", "quotes")],
            "facts": [m["content"] for m in get_fallback_materials("", "facts")],
            "theories": [m["content"] for m in get_fallback_materials("", "theories")],
            "literature": [m["content"] for m in get_fallback_materials("", "literature")],
        }

        return {
            "materials": fallback_materials,
            "current_agent": "librarian",
            "errors": [f"Librarian warning: {str(e)}"],
            "retrieval_metadata": {
                "total": sum(len(v) for v in fallback_materials.values()),
                "sources": {"fallback": sum(len(v) for v in fallback_materials.values())},
            },
        }
