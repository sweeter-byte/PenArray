"""
LangGraph Workflow Definition for BiZhen Multi-Agent System.

Implements the Fan-out/Fan-in architecture with Closed-Loop Revision System.

Sequential Phase:
    Strategist (R1) -> Librarian (V3) -> Outliner (R1)

Fan-out Phase (from Outliner):
    Branch A: Writer_Profound (R1) -> Grader_Profound (R1) -> Reviser_Profound -> Reviewer_Profound
    Branch B: Writer_Rhetorical (V3) -> Grader_Rhetorical (R1) -> Reviser_Rhetorical -> Reviewer_Rhetorical
    Branch C: Writer_Steady (V3) -> Grader_Steady (R1) -> Reviser_Steady -> Reviewer_Steady

Revision Loop (per branch):
    Reviewer decision determines routing:
    - ACCEPT: -> Aggregator (wait for all branches)
    - REVISE: -> Loop back to Reviser (max 3 times)
    - REWRITE: -> Loop back to Writer (max 3 times)

Fan-in Phase:
    All Reviewers (ACCEPT) -> Aggregator -> END

The merge_dicts reducer in EssayState ensures parallel branch results
are properly merged without data loss.
"""

from typing import Any, Dict, Literal

from langgraph.graph import StateGraph, END

from backend.core.state import EssayState, STYLE_PROFOUND, STYLE_RHETORICAL, STYLE_STEADY
from backend.core.agents.strategist import strategist_node
from backend.core.agents.librarian import librarian_node
from backend.core.agents.outliner import outliner_node
from backend.core.agents.writer import (
    writer_profound_node,
    writer_rhetorical_node,
    writer_steady_node,
)
from backend.core.agents.grader import (
    grader_profound_node,
    grader_rhetorical_node,
    grader_steady_node,
)
from backend.core.agents.reviser import (
    reviser_profound_node,
    reviser_rhetorical_node,
    reviser_steady_node,
)
from backend.core.agents.reviewer import (
    reviewer_profound_node,
    reviewer_rhetorical_node,
    reviewer_steady_node,
    get_routing_decision,
)
from backend.core.agents.aggregator import aggregator_node


def create_routing_function(style: str):
    """
    Create a routing function for conditional edges based on reviewer decision.

    Args:
        style: Essay style (profound/rhetorical/steady)

    Returns:
        Routing function that returns "accept", "revise", or "rewrite"
    """
    def route(state: EssayState) -> Literal["accept", "revise", "rewrite"]:
        return get_routing_decision(state, style)
    return route


def create_workflow() -> StateGraph:
    """
    Create and configure the LangGraph workflow with Closed-Loop Revision System.

    The workflow now includes:
    - Reviser nodes: Apply feedback and enforce word count
    - Reviewer nodes: Quality assurance and routing decisions
    - Conditional edges: Route based on ACCEPT/REVISE/REWRITE decisions

    Returns:
        Compiled StateGraph ready for execution
    """
    # Initialize the state graph with EssayState schema
    workflow = StateGraph(EssayState)

    # =========================================
    # PHASE 1: Sequential Nodes
    # =========================================
    # These nodes run in sequence, each building on the previous
    workflow.add_node("strategist", strategist_node)
    workflow.add_node("librarian", librarian_node)
    workflow.add_node("outliner", outliner_node)

    # =========================================
    # PHASE 2: Parallel Writer Nodes (Fan-out)
    # =========================================
    # Three writers run in parallel, each producing a different style
    workflow.add_node("writer_profound", writer_profound_node)
    workflow.add_node("writer_rhetorical", writer_rhetorical_node)
    workflow.add_node("writer_steady", writer_steady_node)

    # =========================================
    # PHASE 3: Parallel Grader Nodes
    # =========================================
    # Each grader evaluates its corresponding writer's output
    workflow.add_node("grader_profound", grader_profound_node)
    workflow.add_node("grader_rhetorical", grader_rhetorical_node)
    workflow.add_node("grader_steady", grader_steady_node)

    # =========================================
    # PHASE 4: Parallel Reviser Nodes (NEW)
    # =========================================
    # Each reviser applies feedback and enforces word count constraints
    workflow.add_node("reviser_profound", reviser_profound_node)
    workflow.add_node("reviser_rhetorical", reviser_rhetorical_node)
    workflow.add_node("reviser_steady", reviser_steady_node)

    # =========================================
    # PHASE 5: Parallel Reviewer Nodes (NEW)
    # =========================================
    # Each reviewer performs QA and makes routing decisions
    workflow.add_node("reviewer_profound", reviewer_profound_node)
    workflow.add_node("reviewer_rhetorical", reviewer_rhetorical_node)
    workflow.add_node("reviewer_steady", reviewer_steady_node)

    # =========================================
    # PHASE 6: Aggregator Node (Fan-in)
    # =========================================
    workflow.add_node("aggregator", aggregator_node)

    # =========================================
    # EDGE DEFINITIONS
    # =========================================

    # --- Sequential Phase Edges ---
    # Entry point: Start with Strategist
    workflow.set_entry_point("strategist")

    # Strategist -> Librarian: Pass angle and thesis for material search
    workflow.add_edge("strategist", "librarian")

    # Librarian -> Outliner: Pass materials for outline generation
    workflow.add_edge("librarian", "outliner")

    # --- Fan-out Edges (from Outliner to Writers) ---
    # Outliner completes -> trigger all three Writers in PARALLEL
    workflow.add_edge("outliner", "writer_profound")
    workflow.add_edge("outliner", "writer_rhetorical")
    workflow.add_edge("outliner", "writer_steady")

    # --- Writer to Grader Edges ---
    # Each Writer's output goes to its corresponding Grader
    workflow.add_edge("writer_profound", "grader_profound")
    workflow.add_edge("writer_rhetorical", "grader_rhetorical")
    workflow.add_edge("writer_steady", "grader_steady")

    # --- Grader to Reviser Edges (NEW) ---
    # Each Grader's feedback goes to its corresponding Reviser
    workflow.add_edge("grader_profound", "reviser_profound")
    workflow.add_edge("grader_rhetorical", "reviser_rhetorical")
    workflow.add_edge("grader_steady", "reviser_steady")

    # --- Reviser to Reviewer Edges (NEW) ---
    # Each Reviser's output goes to its corresponding Reviewer
    workflow.add_edge("reviser_profound", "reviewer_profound")
    workflow.add_edge("reviser_rhetorical", "reviewer_rhetorical")
    workflow.add_edge("reviser_steady", "reviewer_steady")

    # --- Conditional Edges from Reviewers (NEW) ---
    # Reviewer acts as router: ACCEPT->aggregator, REVISE->reviser, REWRITE->writer

    # Profound branch routing
    workflow.add_conditional_edges(
        "reviewer_profound",
        create_routing_function(STYLE_PROFOUND),
        {
            "accept": "aggregator",
            "revise": "reviser_profound",
            "rewrite": "writer_profound",
        }
    )

    # Rhetorical branch routing
    workflow.add_conditional_edges(
        "reviewer_rhetorical",
        create_routing_function(STYLE_RHETORICAL),
        {
            "accept": "aggregator",
            "revise": "reviser_rhetorical",
            "rewrite": "writer_rhetorical",
        }
    )

    # Steady branch routing
    workflow.add_conditional_edges(
        "reviewer_steady",
        create_routing_function(STYLE_STEADY),
        {
            "accept": "aggregator",
            "revise": "reviser_steady",
            "rewrite": "writer_steady",
        }
    )

    # --- Final Edge ---
    # Aggregator -> END: Complete the workflow
    # Note: Aggregator waits for all three branches to reach ACCEPT
    workflow.add_edge("aggregator", END)

    # Compile and return the workflow
    return workflow.compile()


# Global compiled workflow instance
# This is the main entry point for task execution
app = create_workflow()


def run_workflow(
    topic: str,
    task_id: int = None,
    image_url: str = None,
    custom_structure: str = None,
) -> Dict[str, Any]:
    """
    Execute the complete essay generation workflow with Closed-Loop Revision.

    Args:
        topic: Essay topic/prompt text
        task_id: Optional database task ID for SSE events
        image_url: Optional image URL for OCR (future)
        custom_structure: Optional user-defined structure constraints (FR-04)

    Returns:
        Final state dictionary with all generation results
    """
    # Prepare initial state
    initial_state: EssayState = {
        "topic": topic,
        "task_id": task_id,
        "image_url": image_url,
        "custom_structure": custom_structure,  # FR-04: Pass to writers
        # Initialize empty containers for merge_dicts reducer
        "drafts": {},
        "titles": {},
        "scores": {},
        "critiques": {},
        "errors": [],
        # Initialize revision system fields (NEW)
        "revision_count": {},  # Tracks revision iterations per style
        "reviewer_comments": {},  # Reviewer feedback per style
        "clean_word_counts": {},  # Programmatic word counts per style
        "reviewer_decisions": {},  # ACCEPT/REVISE/REWRITE per style
    }

    # Execute workflow
    final_state = app.invoke(initial_state)

    return final_state


# Visualization helper (for debugging)
def get_workflow_diagram() -> str:
    """
    Generate a text representation of the workflow.

    Returns:
        ASCII diagram of the workflow
    """
    diagram = """
    BiZhen Essay Generation Workflow (with Closed-Loop Revision)
    =============================================================

    ┌─────────────┐
    │  STRATEGIST │ (DeepSeek R1)
    │  审题分析    │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │  LIBRARIAN  │ (DeepSeek V3)
    │  素材检索    │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │   OUTLINER  │ (DeepSeek R1)
    │  大纲构思    │
    └──────┬──────┘
           │
    ═══════╪═══════════════════════════════════════════════════════
           │              FAN-OUT (Parallel Branches)
    ┌──────┼──────────────────────┬──────────────────────┐
    │      │                      │                      │
    ▼      ▼                      ▼                      ▼
┌──────────────┐           ┌──────────────┐       ┌──────────────┐
│    WRITER    │           │    WRITER    │       │    WRITER    │
│   PROFOUND   │ (R1)      │  RHETORICAL  │ (V3)  │    STEADY    │ (V3)
│    深刻型    │           │    文采型    │       │    稳健型    │
└──────┬───────┘           └──────┬───────┘       └──────┬───────┘
       │                          │                      │
       ▼                          ▼                      ▼
┌──────────────┐           ┌──────────────┐       ┌──────────────┐
│    GRADER    │           │    GRADER    │       │    GRADER    │
│   PROFOUND   │ (R1)      │  RHETORICAL  │ (R1)  │    STEADY    │ (R1)
│    阅卷      │           │    阅卷      │       │    阅卷      │
└──────┬───────┘           └──────┬───────┘       └──────┬───────┘
       │                          │                      │
       ▼                          ▼                      ▼
┌──────────────┐           ┌──────────────┐       ┌──────────────┐
│   REVISER    │◄──┐       │   REVISER    │◄──┐   │   REVISER    │◄──┐
│   PROFOUND   │   │       │  RHETORICAL  │   │   │    STEADY    │   │
│    修订      │   │       │    修订      │   │   │    修订      │   │
└──────┬───────┘   │       └──────┬───────┘   │   └──────┬───────┘   │
       │           │              │           │          │           │
       ▼           │              ▼           │          ▼           │
┌──────────────┐   │       ┌──────────────┐   │   ┌──────────────┐   │
│   REVIEWER   │───┤       │   REVIEWER   │───┤   │   REVIEWER   │───┤
│   PROFOUND   │   │       │  RHETORICAL  │   │   │    STEADY    │   │
│    审核      │   │       │    审核      │   │   │    审核      │   │
└──────┬───────┘   │       └──────┬───────┘   │   └──────┬───────┘   │
       │           │              │           │          │           │
       │ REVISE────┘              │ REVISE────┘          │ REVISE────┘
       │ REWRITE──────────────────│───────────────────── │ ─────────►Writer
       │ ACCEPT                   │ ACCEPT               │ ACCEPT
       │                          │                      │
    ═══╪══════════════════════════╪══════════════════════╪═══════════
       │         FAN-IN (All Branches Must ACCEPT)       │
       └──────────────────────────┼──────────────────────┘
                                  │
                                  ▼
                         ┌─────────────┐
                         │ AGGREGATOR  │
                         │  结果汇总    │
                         └──────┬──────┘
                                │
                                ▼
                             [ END ]

    Revision Loop Rules:
    ─────────────────────
    • ACCEPT: Essay meets quality standards → proceed to Aggregator
    • REVISE: Minor issues → loop back to Reviser (max 3 times)
    • REWRITE: Major failure → loop back to Writer (max 3 times)
    • Safety Valve: After 3 revisions, force ACCEPT to prevent infinite loops
    """
    return diagram
