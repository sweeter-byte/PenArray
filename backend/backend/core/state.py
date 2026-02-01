"""
LangGraph State Definition for BiZhen Multi-Agent System.

Implements the EssayState TypedDict as defined in LLD Section 1.3.
The merge_dicts reducer is CRITICAL for Fan-in aggregation - it allows
multiple parallel Writer/Grader nodes to update shared dict fields
without overwriting each other's results.

Example Flow:
    WriterProfound returns: {"drafts": {"profound": "..."}}
    WriterRhetorical returns: {"drafts": {"rhetorical": "..."}}
    WriterSteady returns: {"drafts": {"steady": "..."}}

    With merge_dicts reducer, final state.drafts = {
        "profound": "...",
        "rhetorical": "...",
        "steady": "..."
    }
"""

from typing import TypedDict, Annotated, List, Dict, Any, Optional
import operator


def merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two dictionaries for Fan-in aggregation.

    This reducer function is used by LangGraph to combine results from
    parallel branches. When multiple nodes return updates to the same
    dict field, this function merges them instead of overwriting.

    Args:
        a: Existing dictionary in state
        b: New dictionary from node return value

    Returns:
        Merged dictionary with all keys from both inputs

    Example:
        >>> merge_dicts({"profound": "A"}, {"rhetorical": "B"})
        {"profound": "A", "rhetorical": "B"}
    """
    if a is None:
        a = {}
    if b is None:
        b = {}
    return {**a, **b}


class EssayState(TypedDict, total=False):
    """
    Shared state object passed through the LangGraph workflow.

    This state is read and updated by each agent node. Fields using
    the Annotated[..., merge_dicts] pattern support parallel updates
    from Fan-out branches.

    Attributes:
        topic: Original essay prompt/topic from user input
        image_url: Optional URL to topic image (for OCR)
        custom_structure: User-provided structure constraints (FR-04)

        angle: Writing angle determined by Strategist
        thesis: Central thesis statement
        style_params: Per-style writing guidance from Strategist

        materials: Retrieved quotes, facts, and examples from Librarian

        outline: Structured essay outline from Outliner

        drafts: Essay content keyed by style (Fan-in merged)
        titles: Essay titles keyed by style (Fan-in merged)
        scores: Grader scores keyed by style (Fan-in merged)
        critiques: Grader feedback keyed by style (Fan-in merged)

        errors: List of error messages (appended via operator.add)

        current_agent: Name of currently executing agent (for SSE)
        task_id: Database task ID for status updates

        revision_count: Number of revision iterations per style (max 3)
        reviewer_comments: Feedback from Reviewer agent per style
        clean_word_counts: Exact character count per style (programmatic)
        reviewer_decisions: Reviewer routing decision per style (ACCEPT/REVISE/REWRITE)
    """
    # Input fields
    topic: str
    image_url: Optional[str]
    task_id: Optional[int]
    custom_structure: Optional[str]  # FR-04: Custom structure constraints

    # Strategist outputs
    angle: str
    thesis: str
    style_params: Dict[str, Any]

    # Librarian outputs
    materials: Dict[str, List[str]]

    # Outliner outputs
    outline: Dict[str, Any]

    # Writer outputs (Fan-in merged)
    # Each writer adds {"style_name": "content"} which gets merged
    drafts: Annotated[Dict[str, str], merge_dicts]
    titles: Annotated[Dict[str, str], merge_dicts]

    # Grader outputs (Fan-in merged)
    # Each grader adds {"style_name": score} and {"style_name": "critique"}
    scores: Annotated[Dict[str, int], merge_dicts]
    critiques: Annotated[Dict[str, str], merge_dicts]

    # Error tracking (appended, not overwritten)
    errors: Annotated[List[str], operator.add]

    # Metadata for SSE streaming (Last-Write-Wins for parallel updates)
    current_agent: Annotated[str, lambda old, new: new]

    # Revision system fields (Closed-Loop Revision System)
    # Tracks the number of revision iterations to prevent infinite loops
    revision_count: Annotated[Dict[str, int], merge_dicts]
    # Comments from Reviewer agent for guiding revisions
    reviewer_comments: Annotated[Dict[str, str], merge_dicts]
    # Exact character count from programmatic counting (not LLM-estimated)
    clean_word_counts: Annotated[Dict[str, int], merge_dicts]
    # Reviewer decision for each style: ACCEPT, REVISE, or REWRITE
    reviewer_decisions: Annotated[Dict[str, str], merge_dicts]


# Style constants for type safety
STYLE_PROFOUND = "profound"
STYLE_RHETORICAL = "rhetorical"
STYLE_STEADY = "steady"

ALL_STYLES = [STYLE_PROFOUND, STYLE_RHETORICAL, STYLE_STEADY]
