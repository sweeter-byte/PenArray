"""
Writer Agents for BiZhen Multi-Agent System.

Three parallel Writer agents, each producing a different essay style:
- Writer_Profound: DeepSeek R1 - philosophical depth and logical rigor
- Writer_Rhetorical: DeepSeek V3 - literary elegance and rhetorical flourish
- Writer_Steady: DeepSeek V3 - reliable structure and consistent quality

These agents run in PARALLEL (Fan-out from Outliner) and their results
are merged using the merge_dicts reducer in EssayState.
"""

import json
from typing import Any, Dict, List

from langchain_openai import ChatOpenAI

from backend.core.state import EssayState, STYLE_PROFOUND, STYLE_RHETORICAL, STYLE_STEADY
from backend.core.agents.base import (
    get_reasoner_model,
    get_chat_model,
    load_prompt,
    format_prompt,
    invoke_model,
    publish_sse_event,
)


def format_outline_for_prompt(outline: Dict[str, Any]) -> str:
    """
    Format outline dictionary into readable text for the prompt.

    Args:
        outline: Structured outline from Outliner

    Returns:
        Formatted string representation
    """
    parts = []

    parts.append(f"【结构类型】{outline.get('structure_type', '并列式')}")

    intro = outline.get("introduction", {})
    parts.append(f"\n【开头】")
    parts.append(f"  开篇方式：{intro.get('method', '引言式')}")
    parts.append(f"  核心内容：{intro.get('content', '')}")

    parts.append(f"\n【主体】")
    for i, para in enumerate(outline.get("body", []), 1):
        parts.append(f"  分论点{i}：{para.get('sub_thesis', '')}")
        parts.append(f"    论证方法：{para.get('method', '')}")

    conclusion = outline.get("conclusion", {})
    parts.append(f"\n【结尾】")
    parts.append(f"  总结方式：{conclusion.get('method', '总结升华')}")
    parts.append(f"  升华方向：{conclusion.get('elevation', '')}")

    return "\n".join(parts)


def format_materials_for_prompt(materials: Dict[str, List[str]]) -> str:
    """
    Format materials dictionary into text for the prompt.

    Args:
        materials: Dictionary of categorized materials

    Returns:
        Formatted string
    """
    parts = []

    for category, items in materials.items():
        if items:
            category_names = {
                "quotes": "名言警句",
                "facts": "事实论据",
                "theories": "理论支撑",
                "literature": "文学素材",
            }
            parts.append(f"【{category_names.get(category, category)}】")
            for item in items:
                parts.append(f"  - {item}")

    return "\n".join(parts) if parts else "暂无素材"


def extract_essay_content(response: str) -> tuple[str, str]:
    """
    Extract title and content from writer response.

    Args:
        response: Raw model response

    Returns:
        Tuple of (title, content)
    """
    lines = response.strip().split("\n")
    title = ""
    content_start = 0

    # Look for title in first few lines
    for i, line in enumerate(lines[:5]):
        line = line.strip()
        # Common title patterns
        if line.startswith("标题") or line.startswith("题目"):
            title = line.split("：")[-1].split(":")[-1].strip()
            content_start = i + 1
            break
        elif line.startswith("#"):
            title = line.lstrip("#").strip()
            content_start = i + 1
            break
        elif len(line) > 5 and len(line) < 30 and not any(c in line for c in ["，", "。", "、"]):
            # Short line without punctuation might be title
            title = line
            content_start = i + 1
            break

    # Rest is content
    content = "\n".join(lines[content_start:]).strip()

    # If no content extracted, use full response
    if not content:
        content = response.strip()

    # Generate title if not found
    if not title:
        # Use first sentence or portion as title idea
        first_para = content.split("\n")[0][:50] if content else ""
        title = f"论{first_para.split('，')[0]}" if first_para else "议论文"

    return title, content


def writer_profound_node(state: EssayState) -> Dict[str, Any]:
    """
    Writer Profound agent node - generates philosophical depth essay.

    Uses DeepSeek R1 (Reasoner) to create an essay emphasizing:
    - Philosophical depth and logical rigor
    - Abstract thinking and theoretical analysis
    - References to philosophers and classic works

    Args:
        state: Current graph state

    Returns:
        State updates with drafts["profound"] and titles["profound"]

    Edge: writer_profound -> grader_profound
    """
    task_id = state.get("task_id")
    topic = state.get("topic", "")
    thesis = state.get("thesis", "")
    outline = state.get("outline", {})
    materials = state.get("materials", {})
    style_params = state.get("style_params", {}).get("profound", {})
    custom_structure = state.get("custom_structure", "")  # FR-04: Custom constraints

    # Publish start event
    if task_id:
        publish_sse_event(
            task_id=task_id,
            event_type="progress",
            agent="writer_profound",
            message="深刻型写手正在撰写，侧重哲学思辨...",
        )

    try:
        # Load prompt configuration
        prompt_config = load_prompt("writer_profound")

        # Get DeepSeek R1 model for deep reasoning
        model = get_reasoner_model()

        # Format prompt inputs
        outline_text = format_outline_for_prompt(outline)
        materials_text = format_materials_for_prompt(materials)

        # Build system prompt with custom structure if provided (FR-04)
        system_prompt = prompt_config.get("system_prompt", "")
        if custom_structure:
            system_prompt += f"\n\n【用户自定义结构约束 - 请务必优先遵循】\n{custom_structure}"

        user_prompt = format_prompt(
            prompt_config.get("template", ""),
            topic=topic,
            thesis=thesis,
            outline=outline_text,
            materials=materials_text,
            style_params=str(style_params),
        )

        # Invoke model
        response = invoke_model(model, system_prompt, user_prompt)

        # Extract title and content
        title, content = extract_essay_content(response)

        # Publish completion event
        if task_id:
            publish_sse_event(
                task_id=task_id,
                event_type="progress",
                agent="writer_profound",
                message=f"深刻型作文撰写完成：《{title}》",
            )

        # Return updates - these will be merged via merge_dicts
        return {
            "drafts": {STYLE_PROFOUND: content},
            "titles": {STYLE_PROFOUND: title},
            "current_agent": "writer_profound",
        }

    except Exception as e:
        if task_id:
            publish_sse_event(
                task_id=task_id,
                event_type="error",
                agent="writer_profound",
                message=f"深刻型写手失败: {str(e)}",
            )
        return {
            "errors": [f"WriterProfound failed: {str(e)}"],
            "drafts": {STYLE_PROFOUND: ""},
            "titles": {STYLE_PROFOUND: ""},
        }


def writer_rhetorical_node(state: EssayState) -> Dict[str, Any]:
    """
    Writer Rhetorical agent node - generates literary elegance essay.

    Uses DeepSeek V3 (Chat) to create an essay emphasizing:
    - Beautiful prose and rhetorical flourishes
    - Poetic language and imagery
    - Literary references and allusions

    Args:
        state: Current graph state

    Returns:
        State updates with drafts["rhetorical"] and titles["rhetorical"]

    Edge: writer_rhetorical -> grader_rhetorical
    """
    task_id = state.get("task_id")
    topic = state.get("topic", "")
    thesis = state.get("thesis", "")
    outline = state.get("outline", {})
    materials = state.get("materials", {})
    style_params = state.get("style_params", {}).get("rhetorical", {})
    custom_structure = state.get("custom_structure", "")  # FR-04: Custom constraints

    # Publish start event
    if task_id:
        publish_sse_event(
            task_id=task_id,
            event_type="progress",
            agent="writer_rhetorical",
            message="文采型写手正在撰写，注重修辞文采...",
        )

    try:
        # Load prompt configuration
        prompt_config = load_prompt("writer_rhetorical")

        # Get DeepSeek V3 model for creative writing
        model = get_chat_model()

        # Format prompt inputs
        outline_text = format_outline_for_prompt(outline)
        materials_text = format_materials_for_prompt(materials)

        # Build system prompt with custom structure if provided (FR-04)
        system_prompt = prompt_config.get("system_prompt", "")
        if custom_structure:
            system_prompt += f"\n\n【用户自定义结构约束 - 请务必优先遵循】\n{custom_structure}"

        user_prompt = format_prompt(
            prompt_config.get("template", ""),
            topic=topic,
            thesis=thesis,
            outline=outline_text,
            materials=materials_text,
            style_params=str(style_params),
        )

        # Invoke model
        response = invoke_model(model, system_prompt, user_prompt)

        # Extract title and content
        title, content = extract_essay_content(response)

        # Publish completion event
        if task_id:
            publish_sse_event(
                task_id=task_id,
                event_type="progress",
                agent="writer_rhetorical",
                message=f"文采型作文撰写完成：《{title}》",
            )

        return {
            "drafts": {STYLE_RHETORICAL: content},
            "titles": {STYLE_RHETORICAL: title},
            "current_agent": "writer_rhetorical",
        }

    except Exception as e:
        if task_id:
            publish_sse_event(
                task_id=task_id,
                event_type="error",
                agent="writer_rhetorical",
                message=f"文采型写手失败: {str(e)}",
            )
        return {
            "errors": [f"WriterRhetorical failed: {str(e)}"],
            "drafts": {STYLE_RHETORICAL: ""},
            "titles": {STYLE_RHETORICAL: ""},
        }


def writer_steady_node(state: EssayState) -> Dict[str, Any]:
    """
    Writer Steady agent node - generates reliable structured essay.

    Uses DeepSeek V3 (Chat) to create an essay emphasizing:
    - Clear and logical structure
    - Reliable and consistent quality
    - Standard argumentative patterns

    Args:
        state: Current graph state

    Returns:
        State updates with drafts["steady"] and titles["steady"]

    Edge: writer_steady -> grader_steady
    """
    task_id = state.get("task_id")
    topic = state.get("topic", "")
    thesis = state.get("thesis", "")
    outline = state.get("outline", {})
    materials = state.get("materials", {})
    style_params = state.get("style_params", {}).get("steady", {})
    custom_structure = state.get("custom_structure", "")  # FR-04: Custom constraints

    # Publish start event
    if task_id:
        publish_sse_event(
            task_id=task_id,
            event_type="progress",
            agent="writer_steady",
            message="稳健型写手正在撰写，确保结构工整...",
        )

    try:
        # Load prompt configuration
        prompt_config = load_prompt("writer_steady")

        # Get DeepSeek V3 model
        model = get_chat_model()

        # Format prompt inputs
        outline_text = format_outline_for_prompt(outline)
        materials_text = format_materials_for_prompt(materials)

        # Build system prompt with custom structure if provided (FR-04)
        system_prompt = prompt_config.get("system_prompt", "")
        if custom_structure:
            system_prompt += f"\n\n【用户自定义结构约束 - 请务必优先遵循】\n{custom_structure}"

        user_prompt = format_prompt(
            prompt_config.get("template", ""),
            topic=topic,
            thesis=thesis,
            outline=outline_text,
            materials=materials_text,
            style_params=str(style_params),
        )

        # Invoke model
        response = invoke_model(model, system_prompt, user_prompt)

        # Extract title and content
        title, content = extract_essay_content(response)

        # Publish completion event
        if task_id:
            publish_sse_event(
                task_id=task_id,
                event_type="progress",
                agent="writer_steady",
                message=f"稳健型作文撰写完成：《{title}》",
            )

        return {
            "drafts": {STYLE_STEADY: content},
            "titles": {STYLE_STEADY: title},
            "current_agent": "writer_steady",
        }

    except Exception as e:
        if task_id:
            publish_sse_event(
                task_id=task_id,
                event_type="error",
                agent="writer_steady",
                message=f"稳健型写手失败: {str(e)}",
            )
        return {
            "errors": [f"WriterSteady failed: {str(e)}"],
            "drafts": {STYLE_STEADY: ""},
            "titles": {STYLE_STEADY: ""},
        }
