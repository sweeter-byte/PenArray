"""
Reviser Agent for BiZhen Multi-Agent System.

Role: Professional Editor - applies feedback and enforces word count constraints.
Model: DeepSeek R1 (Reasoner) - for precise and logical editing

The Reviser implements a self-correction loop with programmatic word count
verification to ensure essays meet the 850-1050 character target:

1. Generate revision based on feedback
2. Count characters using count_chinese_chars() (NOT LLM estimation)
3. If count is outside range, retry with stronger prompt (max 2 retries)
4. Return revised essay with exact word count

This is part of the Closed-Loop Revision System:
Writer -> Grader -> Reviser -> [Word Count Check] -> Reviewer -> (Router)
"""

from typing import Any, Dict

from backend.core.state import EssayState, STYLE_PROFOUND, STYLE_RHETORICAL, STYLE_STEADY
from backend.core.agents.base import (
    get_reasoner_model,
    load_prompt,
    format_prompt,
    invoke_model,
    publish_sse_event,
)
from backend.core.agents.writer import extract_essay_content
from backend.utils.text_tools import count_chinese_chars, analyze_essay_length


# Word count constraints
MIN_WORD_COUNT = 850
MAX_WORD_COUNT = 1050
TOLERATE_MAX = 1100
MAX_WORD_COUNT_RETRIES = 2


def create_reviser_node(style: str):
    """
    Factory function to create a reviser node for a specific style.

    Args:
        style: Essay style to revise (profound/rhetorical/steady)

    Returns:
        Reviser node function
    """
    style_names = {
        STYLE_PROFOUND: ("深刻型", "reviser_profound"),
        STYLE_RHETORICAL: ("文采型", "reviser_rhetorical"),
        STYLE_STEADY: ("稳健型", "reviser_steady"),
    }
    style_cn, agent_name = style_names.get(style, ("", "reviser"))

    def reviser_node(state: EssayState) -> Dict[str, Any]:
        """
        Reviser agent node - applies feedback and enforces word count.

        Implements a self-correction loop:
        1. Generate revision
        2. Count characters programmatically
        3. If outside 850-1100 range, retry with stronger prompt

        Args:
            state: Current graph state with drafts, critiques, and reviewer feedback

        Returns:
            State updates with revised drafts[style] and clean_word_counts[style]

        Edge: reviser_{style} -> reviewer_{style}
        """
        task_id = state.get("task_id")
        topic = state.get("topic", "")
        drafts = state.get("drafts", {})
        critiques = state.get("critiques", {})
        reviewer_comments = state.get("reviewer_comments", {})
        revision_count = state.get("revision_count", {}).get(style, 0)

        original_essay = drafts.get(style, "")
        grader_feedback = critiques.get(style, "")
        reviewer_feedback = reviewer_comments.get(style, "")

        # Combine feedback sources
        combined_feedback = grader_feedback
        if reviewer_feedback:
            combined_feedback = f"{reviewer_feedback}\n\n【初次评阅反馈】\n{grader_feedback}"

        # Publish start event
        if task_id:
            publish_sse_event(
                task_id=task_id,
                event_type="progress",
                agent=agent_name,
                message=f"正在修订{style_cn}作文（第{revision_count + 1}轮）...",
            )

        # Skip if no essay content
        if not original_essay:
            return {
                "errors": [f"Reviser_{style}: No essay content to revise"],
            }

        try:
            # Load prompt configuration
            prompt_config = load_prompt("reviser")

            # Get DeepSeek R1 model for precise editing
            model = get_reasoner_model()

            # Analyze current word count
            current_count, status, suggestion = analyze_essay_length(original_essay)

            # Determine word count instruction
            if status == "fail" and current_count < MIN_WORD_COUNT:
                word_count_instruction = prompt_config.get(
                    "word_count_instruction_templates", {}
                ).get("expand", "请扩展内容")
                word_count_status = "字数不足"
            elif status == "fail" and current_count > TOLERATE_MAX:
                word_count_instruction = prompt_config.get(
                    "word_count_instruction_templates", {}
                ).get("reduce", "请删减内容")
                word_count_status = "字数过多"
            else:
                word_count_instruction = prompt_config.get(
                    "word_count_instruction_templates", {}
                ).get("maintain", "请保持字数")
                word_count_status = "字数合适"

            system_prompt = prompt_config.get("system_prompt", "")
            user_prompt = format_prompt(
                prompt_config.get("template", ""),
                topic=topic,
                original_essay=original_essay,
                current_word_count=current_count,
                feedback=combined_feedback,
                word_count_status=word_count_status,
                word_count_instruction=word_count_instruction,
            )

            # Self-correction loop for word count enforcement
            revised_essay = ""
            final_count = 0
            retries = 0

            while retries <= MAX_WORD_COUNT_RETRIES:
                # Invoke model
                response = invoke_model(model, system_prompt, user_prompt)

                # Extract essay content
                _, revised_essay = extract_essay_content(response)

                # Programmatic word count verification
                final_count = count_chinese_chars(revised_essay)

                # Check word count constraints
                if MIN_WORD_COUNT <= final_count <= TOLERATE_MAX:
                    # Pass or tolerate - accept the revision
                    break

                # Word count outside acceptable range - retry
                retries += 1

                if retries <= MAX_WORD_COUNT_RETRIES:
                    # Generate stronger prompt for retry
                    if final_count < MIN_WORD_COUNT:
                        direction = "扩展"
                        delta = MIN_WORD_COUNT - final_count
                    else:
                        direction = "删减"
                        delta = final_count - MAX_WORD_COUNT

                    # Update prompt with stronger instruction
                    user_prompt = f"""【重要提醒】
上一次修订的字数为{final_count}字，仍然不在目标范围内（850-1050字）。

请你{direction}约{delta}字，确保最终字数在850-1050字之间。

{user_prompt}"""

                    if task_id:
                        publish_sse_event(
                            task_id=task_id,
                            event_type="progress",
                            agent=agent_name,
                            message=f"字数{final_count}字不达标，正在重新修订（重试{retries}/{MAX_WORD_COUNT_RETRIES}）...",
                        )

            # Determine final status
            _, final_status, _ = analyze_essay_length(revised_essay)

            # Publish completion event
            if task_id:
                status_msg = "达标" if final_status in ["pass", "tolerate"] else "未达标"
                publish_sse_event(
                    task_id=task_id,
                    event_type="progress",
                    agent=agent_name,
                    message=f"{style_cn}作文修订完成：{final_count}字（{status_msg}）",
                )

            # Return updates
            return {
                "drafts": {style: revised_essay},
                "clean_word_counts": {style: final_count},
                "current_agent": agent_name,
            }

        except Exception as e:
            if task_id:
                publish_sse_event(
                    task_id=task_id,
                    event_type="error",
                    agent=agent_name,
                    message=f"{style_cn}修订失败: {str(e)}",
                )
            return {
                "errors": [f"Reviser_{style} failed: {str(e)}"],
            }

    return reviser_node


# Create the three reviser nodes
reviser_profound_node = create_reviser_node(STYLE_PROFOUND)
reviser_rhetorical_node = create_reviser_node(STYLE_RHETORICAL)
reviser_steady_node = create_reviser_node(STYLE_STEADY)
