"""
Grader Agent for BiZhen Multi-Agent System.

Role: Score and critique essays according to Gaokao grading standards.
Model: DeepSeek R1 (Reasoner) - for fair and logical evaluation

Three Grader instances run in parallel (one per style), each evaluating
the corresponding Writer's output. Results are merged via merge_dicts.

Scoring follows the Gaokao standard:
- Total: 60 points
- Content (20): Depth of thought, clarity of thesis, quality of arguments
- Structure (20): Organization, coherence, transitions
- Language (20): Fluency, style, grammar
"""

import re
from typing import Any, Dict, Optional, Tuple

from langchain_openai import ChatOpenAI

from backend.core.state import EssayState, STYLE_PROFOUND, STYLE_RHETORICAL, STYLE_STEADY
from backend.core.agents.base import (
    get_reasoner_model,
    load_prompt,
    format_prompt,
    invoke_model,
    publish_sse_event,
)


def parse_grader_response(response: str) -> Tuple[int, str]:
    """
    Parse grader response to extract score and critique.

    Args:
        response: Raw model response

    Returns:
        Tuple of (total_score, critique_text)
    """
    score = 0
    critique = response

    lines = response.split("\n")

    # Look for score patterns
    for line in lines:
        line = line.strip()

        # Pattern: 总分：XX or 总分: XX or Total: XX
        score_match = re.search(r"总分[：:]\s*(\d+)", line)
        if score_match:
            score = int(score_match.group(1))
            continue

        # Pattern: XX分 or XX/60
        score_match = re.search(r"(\d+)\s*[分/]", line)
        if score_match and not score:
            potential_score = int(score_match.group(1))
            if 0 <= potential_score <= 60:
                score = potential_score

    # Extract critique section
    critique_markers = ["评语", "总体评价", "评分理由", "critique", "总评"]
    for marker in critique_markers:
        if marker in response.lower():
            idx = response.lower().find(marker)
            # Get content after the marker
            after_marker = response[idx:]
            # Find the actual content
            lines_after = after_marker.split("\n")
            critique_lines = []
            for i, l in enumerate(lines_after):
                if i > 0 and l.strip():  # Skip the marker line
                    critique_lines.append(l.strip())
                if len(critique_lines) > 10:
                    break
            if critique_lines:
                critique = "\n".join(critique_lines)
                break

    # Validate score
    if score < 0 or score > 60:
        score = 45  # Default reasonable score

    return score, critique


def create_grader_node(style: str):
    """
    Factory function to create a grader node for a specific style.

    Args:
        style: Essay style to grade (profound/rhetorical/steady)

    Returns:
        Grader node function
    """
    style_names = {
        STYLE_PROFOUND: ("深刻型", "grader_profound"),
        STYLE_RHETORICAL: ("文采型", "grader_rhetorical"),
        STYLE_STEADY: ("稳健型", "grader_steady"),
    }
    style_cn, agent_name = style_names.get(style, ("", "grader"))

    def grader_node(state: EssayState) -> Dict[str, Any]:
        """
        Grader agent node - scores and critiques essay.

        Uses DeepSeek R1 (Reasoner) to provide fair, logical evaluation
        based on Gaokao grading standards.

        Args:
            state: Current graph state with drafts

        Returns:
            State updates with scores[style] and critiques[style]

        Edge: grader_{style} -> aggregator
        """
        task_id = state.get("task_id")
        topic = state.get("topic", "")
        drafts = state.get("drafts", {})
        essay_content = drafts.get(style, "")
        title = state.get("titles", {}).get(style, "")

        # Publish start event
        if task_id:
            publish_sse_event(
                task_id=task_id,
                event_type="progress",
                agent=agent_name,
                message=f"正在评阅{style_cn}作文...",
            )

        # Skip if no essay content
        if not essay_content:
            return {
                "scores": {style: 0},
                "critiques": {style: "未能生成作文内容"},
                "errors": [f"Grader_{style}: No essay content to grade"],
            }

        try:
            # Load prompt configuration
            prompt_config = load_prompt("grader")

            # Get DeepSeek R1 model for logical evaluation
            model = get_reasoner_model()

            system_prompt = prompt_config.get("system_prompt", "")
            user_prompt = format_prompt(
                prompt_config.get("template", ""),
                topic=topic,
                essay_content=essay_content,
                style=style_cn,
            )

            # Invoke model
            response = invoke_model(model, system_prompt, user_prompt)

            # Parse score and critique
            score, critique = parse_grader_response(response)

            # Publish completion event
            if task_id:
                grade_level = get_grade_level(score)
                publish_sse_event(
                    task_id=task_id,
                    event_type="progress",
                    agent=agent_name,
                    message=f"{style_cn}作文评阅完成：{score}分（{grade_level}）",
                )

            # Return updates - merged via merge_dicts
            return {
                "scores": {style: score},
                "critiques": {style: critique},
                "current_agent": agent_name,
            }

        except Exception as e:
            if task_id:
                publish_sse_event(
                    task_id=task_id,
                    event_type="error",
                    agent=agent_name,
                    message=f"{style_cn}评阅失败: {str(e)}",
                )
            return {
                "scores": {style: 0},
                "critiques": {style: f"评阅出错: {str(e)}"},
                "errors": [f"Grader_{style} failed: {str(e)}"],
            }

    return grader_node


def get_grade_level(score: int) -> str:
    """
    Convert score to grade level description.

    Args:
        score: Numerical score (0-60)

    Returns:
        Grade level string in Chinese
    """
    if score >= 50:
        return "一等文"
    elif score >= 40:
        return "二等文"
    elif score >= 30:
        return "三等文"
    else:
        return "四等文"


# Create the three grader nodes
grader_profound_node = create_grader_node(STYLE_PROFOUND)
grader_rhetorical_node = create_grader_node(STYLE_RHETORICAL)
grader_steady_node = create_grader_node(STYLE_STEADY)


# Unified grader function for simplified graph (if needed)
def grader_node(state: EssayState) -> Dict[str, Any]:
    """
    Unified grader that scores all essays.

    This is an alternative implementation that grades all essays
    in a single node instead of three parallel nodes.

    Not used in the Fan-out/Fan-in architecture but provided
    as a fallback option.
    """
    task_id = state.get("task_id")
    drafts = state.get("drafts", {})
    scores = {}
    critiques = {}
    errors = []

    if task_id:
        publish_sse_event(
            task_id=task_id,
            event_type="progress",
            agent="grader",
            message="正在评阅所有作文...",
        )

    for style in [STYLE_PROFOUND, STYLE_RHETORICAL, STYLE_STEADY]:
        essay_content = drafts.get(style, "")
        if essay_content:
            try:
                # Simple scoring based on content length and structure
                word_count = len(essay_content)
                has_structure = any(
                    marker in essay_content
                    for marker in ["首先", "其次", "最后", "综上"]
                )

                # Base score
                if word_count >= 800:
                    score = 45
                elif word_count >= 600:
                    score = 40
                else:
                    score = 35

                # Bonus for structure
                if has_structure:
                    score += 5

                scores[style] = min(score, 60)
                critiques[style] = f"文章结构{'完整' if has_structure else '需要加强'}，字数{word_count}字。"

            except Exception as e:
                scores[style] = 0
                critiques[style] = str(e)
                errors.append(f"Grader error for {style}: {str(e)}")
        else:
            scores[style] = 0
            critiques[style] = "未能生成内容"

    return {
        "scores": scores,
        "critiques": critiques,
        "errors": errors if errors else [],
        "current_agent": "grader",
    }
