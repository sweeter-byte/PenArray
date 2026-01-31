"""
Strategist Agent for BiZhen Multi-Agent System.

Role: Analyze the essay topic and determine the writing angle/thesis.
Model: DeepSeek R1 (Reasoner) - for deep intent analysis

The Strategist is the first agent in the workflow. It:
1. Analyzes the essay topic/prompt
2. Identifies key themes and requirements
3. Determines the central thesis
4. Provides differentiated guidance for each writing style
"""

import json
from typing import Any, Dict

from langchain_openai import ChatOpenAI

from backend.core.state import EssayState
from backend.core.agents.base import (
    get_reasoner_model,
    load_prompt,
    format_prompt,
    invoke_model,
    publish_sse_event,
)


def strategist_node(state: EssayState) -> Dict[str, Any]:
    """
    Strategist agent node - analyzes topic and determines writing angle.

    This is the entry point of the workflow. The Strategist uses DeepSeek R1
    to perform deep analysis of the essay topic and provide strategic guidance
    for all three writing styles.

    Args:
        state: Current graph state containing the topic

    Returns:
        State updates with angle, thesis, and style_params

    Edge: strategist -> librarian
    """
    task_id = state.get("task_id")
    topic = state.get("topic", "")

    # Publish start event
    if task_id:
        publish_sse_event(
            task_id=task_id,
            event_type="progress",
            agent="strategist",
            message="正在分析题目，确定立意角度...",
        )

    try:
        # Load prompt configuration
        prompt_config = load_prompt("strategist")

        # Get DeepSeek R1 model for deep reasoning
        model = get_reasoner_model()

        # Format the prompt with topic
        system_prompt = prompt_config.get("system_prompt", "")
        user_prompt = format_prompt(
            prompt_config.get("template", "{topic}"),
            topic=topic,
        )

        # Invoke model
        response = invoke_model(model, system_prompt, user_prompt)

        # Parse response - extract structured data
        # The model should return analysis with angle, thesis, and style params
        result = parse_strategist_response(response, topic)

        # Publish completion event
        if task_id:
            publish_sse_event(
                task_id=task_id,
                event_type="progress",
                agent="strategist",
                message=f"审题完成，立意角度：{result.get('angle', '待定')}",
            )

        return {
            "angle": result.get("angle", ""),
            "thesis": result.get("thesis", ""),
            "style_params": result.get("style_params", {}),
            "current_agent": "strategist",
        }

    except Exception as e:
        if task_id:
            publish_sse_event(
                task_id=task_id,
                event_type="error",
                agent="strategist",
                message=f"策划失败: {str(e)}",
            )
        return {
            "errors": [f"Strategist failed: {str(e)}"],
            "angle": "",
            "thesis": "",
            "style_params": {},
        }


def parse_strategist_response(response: str, topic: str) -> Dict[str, Any]:
    """
    Parse the Strategist's response to extract structured data.

    Attempts to extract:
    - angle: The chosen writing angle/perspective
    - thesis: The central thesis statement
    - style_params: Differentiated guidance for each style

    Args:
        response: Raw model response text
        topic: Original topic (fallback)

    Returns:
        Parsed dictionary with angle, thesis, and style_params
    """
    result = {
        "angle": "",
        "thesis": "",
        "style_params": {
            "profound": {"focus": "", "method": "", "references": []},
            "rhetorical": {"focus": "", "rhetoric": [], "references": []},
            "steady": {"structure": "", "layers": []},
        },
    }

    # Try to extract angle from response
    lines = response.split("\n")
    for i, line in enumerate(lines):
        line_lower = line.lower()

        # Look for angle/thesis markers
        if "中心论点" in line or "thesis" in line_lower:
            # Get the content after the marker or next line
            content = line.split("：")[-1].split(":")[-1].strip()
            if content:
                result["thesis"] = content
            elif i + 1 < len(lines):
                result["thesis"] = lines[i + 1].strip()

        if "立意" in line or "angle" in line_lower:
            content = line.split("：")[-1].split(":")[-1].strip()
            if content:
                result["angle"] = content
            elif i + 1 < len(lines):
                result["angle"] = lines[i + 1].strip()

        # Look for style-specific guidance
        if "深刻型" in line or "profound" in line_lower:
            # Extract profound style params
            result["style_params"]["profound"]["focus"] = extract_section_content(
                lines, i, ["哲学", "思辨", "focus"]
            )

        if "文采型" in line or "rhetorical" in line_lower:
            result["style_params"]["rhetorical"]["focus"] = extract_section_content(
                lines, i, ["修辞", "文学", "focus"]
            )

        if "稳健型" in line or "steady" in line_lower:
            result["style_params"]["steady"]["structure"] = extract_section_content(
                lines, i, ["结构", "框架", "structure"]
            )

    # Fallback: use first substantial paragraph as angle
    if not result["angle"]:
        for line in lines:
            if len(line.strip()) > 20:
                result["angle"] = line.strip()[:100]
                break

    # Fallback thesis
    if not result["thesis"]:
        result["thesis"] = f"关于'{topic}'的深入思考"

    return result


def extract_section_content(lines: list, start_idx: int, keywords: list) -> str:
    """
    Extract content from a section starting at given index.

    Args:
        lines: All response lines
        start_idx: Starting line index
        keywords: Keywords to look for

    Returns:
        Extracted content string
    """
    content_parts = []
    for i in range(start_idx, min(start_idx + 5, len(lines))):
        line = lines[i].strip()
        if line and not line.startswith("#"):
            for kw in keywords:
                if kw in line:
                    # Extract content after the keyword
                    parts = line.split("：")
                    if len(parts) > 1:
                        content_parts.append(parts[-1].strip())
                    else:
                        parts = line.split(":")
                        if len(parts) > 1:
                            content_parts.append(parts[-1].strip())

    return " ".join(content_parts) if content_parts else ""
