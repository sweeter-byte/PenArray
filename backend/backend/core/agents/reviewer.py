"""
Reviewer Agent for BiZhen Multi-Agent System.

Role: Quality Assurance / Gatekeeper - Final audit before delivery.
Model: DeepSeek R1 (Reasoner) - for thorough and logical evaluation

The Reviewer acts as the intelligent router in the Closed-Loop Revision System:
- ACCEPT: Quality met. Essay goes to Aggregator.
- REVISE: Minor issues. Loop back to Reviser.
- REWRITE: Major failure. Loop back to Writer.

Safety Valve: Enforces max_revision_loop = 3 to prevent infinite loops.
If revision_count > 3, forces ACCEPT with a warning.

Checklist:
1. Structure: Full Introduction/Body/Conclusion?
2. Relevance: On-topic?
3. Reality Check: Are quotes/facts real? (Hallucination check)
4. Language: Grammar and fluency
"""

import json
import re
from typing import Any, Dict, Tuple

from backend.core.state import EssayState, STYLE_PROFOUND, STYLE_RHETORICAL, STYLE_STEADY
from backend.core.agents.base import (
    get_reasoner_model,
    load_prompt,
    format_prompt,
    invoke_model,
    publish_sse_event,
)
from backend.utils.text_tools import count_chinese_chars, check_essay_structure


# Maximum revision loops before forced acceptance
MAX_REVISION_LOOPS = 3

# Valid actions
VALID_ACTIONS = {"ACCEPT", "REVISE", "REWRITE"}


def parse_reviewer_response(response: str) -> Tuple[str, float, list, str]:
    """
    Parse reviewer response to extract decision JSON.

    Expected format:
    ```json
    {
        "action": "ACCEPT" | "REVISE" | "REWRITE",
        "confidence": 0.0-1.0,
        "issues": ["issue1", "issue2"],
        "comments": "detailed comments"
    }
    ```

    Args:
        response: Raw model response

    Returns:
        Tuple of (action, confidence, issues, comments)
    """
    action = "ACCEPT"
    confidence = 0.8
    issues = []
    comments = ""

    # Try to find JSON block in response
    json_patterns = [
        r'```json\s*(.*?)\s*```',  # Markdown code block
        r'```\s*(.*?)\s*```',      # Generic code block
        r'\{[^{}]*"action"[^{}]*\}',  # Inline JSON
    ]

    json_str = None
    for pattern in json_patterns:
        match = re.search(pattern, response, re.DOTALL)
        if match:
            json_str = match.group(1) if '```' in pattern else match.group(0)
            break

    if json_str:
        try:
            # Clean up the JSON string
            json_str = json_str.strip()
            data = json.loads(json_str)

            action = data.get("action", "ACCEPT").upper()
            confidence = float(data.get("confidence", 0.8))
            issues = data.get("issues", [])
            comments = data.get("comments", "")

            # Validate action
            if action not in VALID_ACTIONS:
                action = "ACCEPT"

        except json.JSONDecodeError:
            # Fallback: try to extract action from text
            pass

    # Fallback: search for action keywords in response
    if action == "ACCEPT" and json_str is None:
        response_upper = response.upper()
        if "REWRITE" in response_upper or "重写" in response:
            action = "REWRITE"
        elif "REVISE" in response_upper or "修改" in response or "修订" in response:
            action = "REVISE"

        # Extract comments from non-JSON response
        comments = response[:500] if len(response) > 500 else response

    return action, confidence, issues, comments


def create_reviewer_node(style: str):
    """
    Factory function to create a reviewer node for a specific style.

    Args:
        style: Essay style to review (profound/rhetorical/steady)

    Returns:
        Reviewer node function
    """
    style_names = {
        STYLE_PROFOUND: ("深刻型", "reviewer_profound"),
        STYLE_RHETORICAL: ("文采型", "reviewer_rhetorical"),
        STYLE_STEADY: ("稳健型", "reviewer_steady"),
    }
    style_cn, agent_name = style_names.get(style, ("", "reviewer"))

    def reviewer_node(state: EssayState) -> Dict[str, Any]:
        """
        Reviewer agent node - quality assurance and routing decision.

        Performs final audit and determines next action:
        - ACCEPT: Quality met, proceed to Aggregator
        - REVISE: Minor issues, loop back to Reviser
        - REWRITE: Major failure, loop back to Writer

        Safety valve: Forces ACCEPT after 3 revision loops.

        Args:
            state: Current graph state with revised drafts

        Returns:
            State updates with reviewer_decisions[style], reviewer_comments[style],
            and incremented revision_count[style]

        Edge: Conditional based on action
            - ACCEPT -> aggregator
            - REVISE -> reviser_{style}
            - REWRITE -> writer_{style}
        """
        task_id = state.get("task_id")
        topic = state.get("topic", "")
        drafts = state.get("drafts", {})
        clean_word_counts = state.get("clean_word_counts", {})
        revision_counts = state.get("revision_count", {})

        essay_content = drafts.get(style, "")
        word_count = clean_word_counts.get(style, 0)
        current_revision_count = revision_counts.get(style, 0)

        # Calculate word count if not already done
        if word_count == 0:
            word_count = count_chinese_chars(essay_content)

        # Publish start event
        if task_id:
            publish_sse_event(
                task_id=task_id,
                event_type="progress",
                agent=agent_name,
                message=f"正在审核{style_cn}作文...",
            )

        # Skip if no essay content
        if not essay_content:
            return {
                "reviewer_decisions": {style: "ACCEPT"},
                "reviewer_comments": {style: "无内容可审核"},
                "revision_count": {style: current_revision_count},
                "errors": [f"Reviewer_{style}: No essay content to review"],
            }

        # Safety valve: Force ACCEPT after max revisions
        if current_revision_count >= MAX_REVISION_LOOPS:
            if task_id:
                publish_sse_event(
                    task_id=task_id,
                    event_type="progress",
                    agent=agent_name,
                    message=f"{style_cn}已达最大修订次数（{MAX_REVISION_LOOPS}轮），强制通过。",
                )
            return {
                "reviewer_decisions": {style: "ACCEPT"},
                "reviewer_comments": {style: f"已达到最大修订次数（{MAX_REVISION_LOOPS}轮），强制通过审核。"},
                "revision_count": {style: current_revision_count},
                "current_agent": agent_name,
            }

        try:
            # Load prompt configuration
            prompt_config = load_prompt("reviewer")

            # Get DeepSeek R1 model for thorough evaluation
            model = get_reasoner_model()

            # Check essay structure programmatically
            structure_check = check_essay_structure(essay_content)

            system_prompt = prompt_config.get("system_prompt", "")
            user_prompt = format_prompt(
                prompt_config.get("template", ""),
                topic=topic,
                essay_content=essay_content,
                style=style_cn,
                word_count=word_count,
                revision_count=current_revision_count + 1,
            )

            # Invoke model
            response = invoke_model(model, system_prompt, user_prompt)

            # Parse decision
            action, confidence, issues, comments = parse_reviewer_response(response)

            # Apply safety rules
            # 1. If structure is incomplete, suggest REVISE (not REWRITE)
            if not structure_check["is_complete"] and action == "ACCEPT":
                action = "REVISE"
                comments = f"结构不完整：{structure_check['feedback']}\n{comments}"
                issues.append(structure_check["feedback"])

            # 2. At revision count 2+, prefer ACCEPT or REVISE over REWRITE
            if current_revision_count >= 2 and action == "REWRITE":
                action = "REVISE"
                comments = f"[已修订{current_revision_count}轮，降级为小修]\n{comments}"

            # Increment revision count for next iteration
            new_revision_count = current_revision_count + 1

            # Publish completion event
            if task_id:
                action_cn = {
                    "ACCEPT": "通过",
                    "REVISE": "需要小修",
                    "REWRITE": "需要重写",
                }.get(action, action)
                publish_sse_event(
                    task_id=task_id,
                    event_type="progress",
                    agent=agent_name,
                    message=f"{style_cn}作文审核完成：{action_cn}（置信度{confidence:.0%}）",
                )

            # Return updates
            return {
                "reviewer_decisions": {style: action},
                "reviewer_comments": {style: comments},
                "revision_count": {style: new_revision_count},
                "clean_word_counts": {style: word_count},
                "current_agent": agent_name,
            }

        except Exception as e:
            if task_id:
                publish_sse_event(
                    task_id=task_id,
                    event_type="error",
                    agent=agent_name,
                    message=f"{style_cn}审核失败: {str(e)}",
                )
            # On error, default to ACCEPT to prevent blocking
            return {
                "reviewer_decisions": {style: "ACCEPT"},
                "reviewer_comments": {style: f"审核出错: {str(e)}"},
                "revision_count": {style: current_revision_count},
                "errors": [f"Reviewer_{style} failed: {str(e)}"],
            }

    return reviewer_node


# Create the three reviewer nodes
reviewer_profound_node = create_reviewer_node(STYLE_PROFOUND)
reviewer_rhetorical_node = create_reviewer_node(STYLE_RHETORICAL)
reviewer_steady_node = create_reviewer_node(STYLE_STEADY)


def get_routing_decision(state: EssayState, style: str) -> str:
    """
    Get the routing decision for a specific style.

    Used by conditional edges in the graph to determine next node.

    Args:
        state: Current graph state
        style: Essay style

    Returns:
        "accept", "revise", or "rewrite"
    """
    decisions = state.get("reviewer_decisions", {})
    decision = decisions.get(style, "ACCEPT").upper()

    if decision == "REWRITE":
        return "rewrite"
    elif decision == "REVISE":
        return "revise"
    else:
        return "accept"
