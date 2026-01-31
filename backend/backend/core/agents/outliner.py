"""
Outliner Agent for BiZhen Multi-Agent System.

Role: Generate structured essay outline based on angle and materials.
Model: DeepSeek R1 (Reasoner) - for logical structure design

The Outliner creates a comprehensive writing blueprint that:
1. Defines the essay structure (parallel/progressive/comparative)
2. Allocates materials to appropriate sections
3. Provides guidance for all three writing styles
"""

import json
from typing import Any, Dict, List

from langchain_openai import ChatOpenAI

from backend.core.state import EssayState
from backend.core.agents.base import (
    get_reasoner_model,
    load_prompt,
    format_prompt,
    invoke_model,
    publish_sse_event,
)


def outliner_node(state: EssayState) -> Dict[str, Any]:
    """
    Outliner agent node - generates structured essay outline.

    Uses DeepSeek R1 to create a logical, well-structured outline
    that can be used by all three Writer agents.

    Args:
        state: Current graph state with thesis and materials

    Returns:
        State updates with outline dictionary

    Edge: outliner -> [writer_profound, writer_rhetorical, writer_steady] (Fan-out)
    """
    task_id = state.get("task_id")
    topic = state.get("topic", "")
    thesis = state.get("thesis", "")
    angle = state.get("angle", "")
    materials = state.get("materials", {})

    # Publish start event
    if task_id:
        publish_sse_event(
            task_id=task_id,
            event_type="progress",
            agent="outliner",
            message="正在构思文章结构，生成写作大纲...",
        )

    try:
        # Load prompt configuration
        prompt_config = load_prompt("outliner")

        # Get DeepSeek R1 model for logical structure
        model = get_reasoner_model()

        # Format materials for prompt
        materials_text = format_materials_for_prompt(materials)

        # Format the prompt
        system_prompt = prompt_config.get("system_prompt", "")
        user_prompt = format_prompt(
            prompt_config.get("template", ""),
            thesis=thesis,
            angle=angle,
            materials=materials_text,
        )

        # Invoke model
        response = invoke_model(model, system_prompt, user_prompt)

        # Parse response to extract outline structure
        outline = parse_outliner_response(response, thesis)

        # Publish completion event
        structure_type = outline.get("structure_type", "并列式")
        if task_id:
            publish_sse_event(
                task_id=task_id,
                event_type="progress",
                agent="outliner",
                message=f"大纲构思完成，采用{structure_type}结构",
                data=outline,
            )

        return {
            "outline": outline,
            "current_agent": "outliner",
        }

    except Exception as e:
        if task_id:
            publish_sse_event(
                task_id=task_id,
                event_type="error",
                agent="outliner",
                message=f"大纲构思失败: {str(e)}",
            )
        # Return basic outline on error
        return {
            "outline": create_fallback_outline(thesis, materials),
            "errors": [f"Outliner warning: {str(e)}"],
        }


def format_materials_for_prompt(materials: Dict[str, List[str]]) -> str:
    """
    Format materials dictionary into a readable string for the prompt.

    Args:
        materials: Dictionary of categorized materials

    Returns:
        Formatted string representation
    """
    parts = []

    if materials.get("quotes"):
        parts.append("【名言警句】")
        for i, quote in enumerate(materials["quotes"], 1):
            parts.append(f"  {i}. {quote}")

    if materials.get("facts"):
        parts.append("【事实论据】")
        for i, fact in enumerate(materials["facts"], 1):
            parts.append(f"  {i}. {fact}")

    if materials.get("theories"):
        parts.append("【理论支撑】")
        for i, theory in enumerate(materials["theories"], 1):
            parts.append(f"  {i}. {theory}")

    if materials.get("literature"):
        parts.append("【文学素材】")
        for i, lit in enumerate(materials["literature"], 1):
            parts.append(f"  {i}. {lit}")

    return "\n".join(parts) if parts else "暂无素材"


def parse_outliner_response(response: str, thesis: str) -> Dict[str, Any]:
    """
    Parse the Outliner's response to extract structured outline.

    Args:
        response: Raw model response text
        thesis: Central thesis for fallback

    Returns:
        Structured outline dictionary
    """
    outline = {
        "structure_type": "并列式",
        "introduction": {
            "method": "引言式",
            "content": "",
            "word_count": 100,
        },
        "body": [],
        "conclusion": {
            "method": "总结升华",
            "elevation": "",
            "word_count": 100,
        },
    }

    lines = response.split("\n")
    current_section = None
    current_body_item = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Detect structure type
        if "并列" in line:
            outline["structure_type"] = "并列式"
        elif "递进" in line or "层进" in line:
            outline["structure_type"] = "递进式"
        elif "对比" in line:
            outline["structure_type"] = "对比式"

        # Detect sections
        if "开头" in line or "第一部分" in line or "引言" in line:
            current_section = "introduction"
        elif "主体" in line or "第二部分" in line or "论证" in line:
            current_section = "body"
        elif "结尾" in line or "第三部分" in line or "结论" in line:
            current_section = "conclusion"

        # Parse introduction
        if current_section == "introduction":
            if "开篇方式" in line or "方式" in line:
                method = line.split("：")[-1].split(":")[-1].strip()
                if method:
                    outline["introduction"]["method"] = method
            elif "内容" in line:
                content = line.split("：")[-1].split(":")[-1].strip()
                if content:
                    outline["introduction"]["content"] = content

        # Parse body paragraphs
        if current_section == "body":
            if "分论点" in line or "论点" in line:
                # Start a new body paragraph
                sub_thesis = line.split("：")[-1].split(":")[-1].strip()
                if sub_thesis and len(sub_thesis) > 5:
                    current_body_item = {
                        "sub_thesis": sub_thesis,
                        "method": "",
                        "materials": [],
                        "word_count": 200,
                    }
                    outline["body"].append(current_body_item)
            elif current_body_item:
                if "论证方法" in line or "方法" in line:
                    method = line.split("：")[-1].split(":")[-1].strip()
                    current_body_item["method"] = method
                elif "素材" in line or "论据" in line:
                    mat = line.split("：")[-1].split(":")[-1].strip()
                    if mat:
                        current_body_item["materials"].append(mat)

        # Parse conclusion
        if current_section == "conclusion":
            if "升华" in line:
                elevation = line.split("：")[-1].split(":")[-1].strip()
                if elevation:
                    outline["conclusion"]["elevation"] = elevation
            elif "方式" in line or "方法" in line:
                method = line.split("：")[-1].split(":")[-1].strip()
                if method:
                    outline["conclusion"]["method"] = method

    # Ensure we have at least some body paragraphs
    if not outline["body"]:
        outline["body"] = create_default_body_paragraphs(thesis)

    return outline


def create_default_body_paragraphs(thesis: str) -> List[Dict[str, Any]]:
    """
    Create default body paragraphs when parsing fails.

    Args:
        thesis: Central thesis

    Returns:
        List of default body paragraph dictionaries
    """
    return [
        {
            "sub_thesis": f"首先，{thesis}的内涵与意义",
            "method": "例证法",
            "materials": [],
            "word_count": 200,
        },
        {
            "sub_thesis": f"其次，如何践行{thesis}",
            "method": "引证法",
            "materials": [],
            "word_count": 200,
        },
        {
            "sub_thesis": f"再者，{thesis}对当代青年的启示",
            "method": "对比论证",
            "materials": [],
            "word_count": 200,
        },
    ]


def create_fallback_outline(thesis: str, materials: Dict[str, List[str]]) -> Dict[str, Any]:
    """
    Create a basic fallback outline when the agent fails.

    Args:
        thesis: Central thesis
        materials: Available materials

    Returns:
        Basic outline structure
    """
    return {
        "structure_type": "并列式",
        "introduction": {
            "method": "引言式",
            "content": f"以{thesis}为核心展开论述",
            "word_count": 100,
        },
        "body": create_default_body_paragraphs(thesis),
        "conclusion": {
            "method": "总结升华",
            "elevation": "呼应开头，升华主题",
            "word_count": 100,
        },
    }
