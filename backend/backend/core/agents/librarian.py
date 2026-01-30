"""
Librarian Agent for BiZhen Multi-Agent System.

Role: Retrieve relevant materials (quotes, facts, examples) for essay writing.
Model: DeepSeek V3 (Chat) - for tool calling and creative retrieval

The Librarian uses RAG (Retrieval-Augmented Generation) to:
1. Search the vector database for relevant quotes and examples
2. Filter and rank materials by relevance and novelty
3. Organize materials by category for easy use by Writers
"""

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


# Placeholder for ChromaDB client - will be initialized when needed
_chroma_client = None


def get_chroma_collection():
    """
    Get or create ChromaDB collection for materials.

    Returns:
        ChromaDB collection instance
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
    Search materials from vector database.

    Args:
        query: Search query text
        category: Optional category filter (quote/fact/theory/literature)
        top_k: Number of results to return

    Returns:
        List of material dictionaries with content and metadata
    """
    collection = get_chroma_collection()

    if collection is None:
        # Return mock data if ChromaDB is not available
        return get_fallback_materials(query, category)

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
                    "tags": metadata.get("tags", []),
                })

        return materials

    except Exception as e:
        print(f"Warning: ChromaDB query failed: {e}")
        return get_fallback_materials(query, category)


def get_fallback_materials(query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Provide fallback materials when ChromaDB is unavailable.

    These are commonly used Gaokao essay materials.
    """
    # Common high-quality materials for Gaokao essays
    fallback = {
        "quotes": [
            {"content": "路漫漫其修远兮，吾将上下而求索。——屈原", "author": "屈原", "tags": ["奋斗", "追求"]},
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
            {"content": "习近平总书记指出：'青年兴则国家兴，青年强则国家强。'", "author": "", "tags": ["青年", "担当"]},
        ],
        "literature": [
            {"content": "沉舟侧畔千帆过，病树前头万木春。——刘禹锡《酬乐天扬州初逢席上见赠》", "author": "刘禹锡", "tags": ["乐观", "发展"]},
            {"content": "长风破浪会有时，直挂云帆济沧海。——李白《行路难》", "author": "李白", "tags": ["理想", "奋斗"]},
            {"content": "千淘万漉虽辛苦，吹尽狂沙始到金。——刘禹锡", "author": "刘禹锡", "tags": ["坚持", "奋斗"]},
        ],
    }

    results = []
    if category and category in fallback:
        results = [{"content": m["content"], "category": category, **m} for m in fallback[category]]
    else:
        # Return mixed materials
        for cat, items in fallback.items():
            results.extend([{"content": m["content"], "category": cat, **m} for m in items[:2]])

    return results[:5]


def librarian_node(state: EssayState) -> Dict[str, Any]:
    """
    Librarian agent node - retrieves relevant materials via RAG.

    Uses DeepSeek V3 for intelligent material selection and organization.
    Searches the vector database and returns categorized materials.

    Args:
        state: Current graph state with angle and thesis

    Returns:
        State updates with materials dictionary

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
        # Load prompt configuration
        prompt_config = load_prompt("librarian")

        # Get DeepSeek V3 model
        model = get_chat_model()

        # Build search query from angle and thesis
        search_query = f"{topic} {angle} {thesis}"

        # Retrieve materials from different categories
        materials = {
            "quotes": [],
            "facts": [],
            "theories": [],
            "literature": [],
        }

        # Search each category
        for category in materials.keys():
            results = search_materials(search_query, category=category, top_k=3)
            materials[category] = [r["content"] for r in results]

        # Use model to select and filter the most relevant materials
        system_prompt = prompt_config.get("system_prompt", "")
        user_prompt = format_prompt(
            prompt_config.get("template", ""),
            angle=angle,
            thesis=thesis,
            style_params=str(state.get("style_params", {})),
        )

        # Optionally, ask model to refine/select materials
        # For now, we use the RAG results directly

        # Publish completion event
        total_materials = sum(len(v) for v in materials.values())
        if task_id:
            publish_sse_event(
                task_id=task_id,
                event_type="progress",
                agent="librarian",
                message=f"素材检索完成，共找到 {total_materials} 条相关素材",
            )

        return {
            "materials": materials,
            "current_agent": "librarian",
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
        return {
            "materials": {
                "quotes": [m["content"] for m in get_fallback_materials("", "quotes")],
                "facts": [m["content"] for m in get_fallback_materials("", "facts")],
                "theories": [],
                "literature": [m["content"] for m in get_fallback_materials("", "literature")],
            },
            "errors": [f"Librarian warning: {str(e)}"],
        }
