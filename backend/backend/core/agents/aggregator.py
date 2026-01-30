"""
Aggregator Node for BiZhen Multi-Agent System.

Role: Collect and validate results from all parallel branches.
Model: None (pure logic node)

The Aggregator is the Fan-in convergence point where:
1. All three Grader results are collected
2. Results are validated for completeness
3. Partial failures are handled gracefully
4. Final completion event is published
"""

from typing import Any, Dict, List

from backend.core.state import EssayState, STYLE_PROFOUND, STYLE_RHETORICAL, STYLE_STEADY, ALL_STYLES
from backend.core.agents.base import publish_sse_event


def aggregator_node(state: EssayState) -> Dict[str, Any]:
    """
    Aggregator node - collects and validates all generation results.

    This is the final node before END. It:
    1. Verifies all expected results are present
    2. Handles partial failures gracefully
    3. Logs any errors that occurred during generation
    4. Publishes the final completion SSE event

    Args:
        state: Final graph state with all merged results

    Returns:
        State updates (minimal, mostly validation)

    Edge: aggregator -> END
    """
    task_id = state.get("task_id")
    drafts = state.get("drafts", {})
    scores = state.get("scores", {})
    critiques = state.get("critiques", {})
    titles = state.get("titles", {})
    errors = state.get("errors", [])

    # Publish aggregation start
    if task_id:
        publish_sse_event(
            task_id=task_id,
            event_type="progress",
            agent="aggregator",
            message="正在汇总所有生成结果...",
        )

    # Validate results
    validation_errors = []
    successful_styles = []
    failed_styles = []

    for style in ALL_STYLES:
        draft = drafts.get(style, "")
        if draft and len(draft) > 100:  # Minimum viable essay length
            successful_styles.append(style)
        else:
            failed_styles.append(style)
            validation_errors.append(f"Style '{style}' has no valid content")

    # Determine overall status
    if len(successful_styles) == 0:
        # Total failure - no essays generated
        if task_id:
            publish_sse_event(
                task_id=task_id,
                event_type="error",
                agent="aggregator",
                message="生成失败：未能生成任何作文",
                data={"errors": errors + validation_errors},
            )
        return {
            "errors": errors + validation_errors + ["All writers failed to produce content"],
            "current_agent": "aggregator",
        }

    elif len(successful_styles) < 3:
        # Partial success - some essays generated
        style_names = {
            STYLE_PROFOUND: "深刻型",
            STYLE_RHETORICAL: "文采型",
            STYLE_STEADY: "稳健型",
        }
        success_names = [style_names[s] for s in successful_styles]
        failed_names = [style_names[s] for s in failed_styles]

        if task_id:
            publish_sse_event(
                task_id=task_id,
                event_type="progress",
                agent="aggregator",
                message=f"部分成功：{', '.join(success_names)} 生成完成，{', '.join(failed_names)} 生成失败",
            )

        # Continue with partial results
        return {
            "errors": errors + validation_errors,
            "current_agent": "aggregator",
        }

    else:
        # Full success - all essays generated
        # Calculate average score
        total_score = sum(scores.get(style, 0) for style in ALL_STYLES)
        avg_score = total_score / 3 if total_score > 0 else 0

        # Find best essay
        best_style = max(ALL_STYLES, key=lambda s: scores.get(s, 0))
        best_score = scores.get(best_style, 0)
        style_names = {
            STYLE_PROFOUND: "深刻型",
            STYLE_RHETORICAL: "文采型",
            STYLE_STEADY: "稳健型",
        }

        if task_id:
            publish_sse_event(
                task_id=task_id,
                event_type="end",
                agent="aggregator",
                message=f"生成完成！最高分：{style_names[best_style]} {best_score}分，平均分：{avg_score:.1f}分",
                data={
                    "status": "completed",
                    "avg_score": avg_score,
                    "best_style": best_style,
                    "best_score": best_score,
                },
            )

        return {
            "current_agent": "aggregator",
        }


def get_generation_summary(state: EssayState) -> Dict[str, Any]:
    """
    Generate a summary of the generation results.

    Args:
        state: Final graph state

    Returns:
        Summary dictionary with statistics
    """
    drafts = state.get("drafts", {})
    scores = state.get("scores", {})
    titles = state.get("titles", {})

    summary = {
        "total_essays": 0,
        "essays": [],
        "avg_score": 0,
        "best_style": None,
        "best_score": 0,
    }

    total_score = 0
    for style in ALL_STYLES:
        draft = drafts.get(style, "")
        if draft:
            score = scores.get(style, 0)
            essay_info = {
                "style": style,
                "title": titles.get(style, ""),
                "word_count": len(draft),
                "score": score,
            }
            summary["essays"].append(essay_info)
            summary["total_essays"] += 1
            total_score += score

            if score > summary["best_score"]:
                summary["best_score"] = score
                summary["best_style"] = style

    if summary["total_essays"] > 0:
        summary["avg_score"] = total_score / summary["total_essays"]

    return summary
