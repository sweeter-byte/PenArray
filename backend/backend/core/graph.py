"""
LangGraph Workflow Definition for BiZhen Multi-Agent System.

Implements the Fan-out/Fan-in architecture as specified in HLD Section 2.1:

Sequential Phase:
    Strategist (R1) -> Librarian (V3) -> Outliner (R1)

Fan-out Phase (from Outliner):
    Branch A: Writer_Profound (R1) -> Grader_Profound (R1)
    Branch B: Writer_Rhetorical (V3) -> Grader_Rhetorical (R1)
    Branch C: Writer_Steady (V3) -> Grader_Steady (R1)

Fan-in Phase:
    All Graders -> Aggregator -> END

The merge_dicts reducer in EssayState ensures parallel branch results
are properly merged without data loss.
"""

from typing import Any, Dict

from langgraph.graph import StateGraph, END

from backend.core.state import EssayState
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
from backend.core.agents.aggregator import aggregator_node


def create_workflow() -> StateGraph:
    """
    Create and configure the LangGraph workflow.

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
    # PHASE 4: Aggregator Node (Fan-in)
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
    # LangGraph handles parallel execution when multiple edges
    # originate from the same node
    workflow.add_edge("outliner", "writer_profound")
    workflow.add_edge("outliner", "writer_rhetorical")
    workflow.add_edge("outliner", "writer_steady")

    # --- Writer to Grader Edges ---
    # Each Writer's output goes to its corresponding Grader
    workflow.add_edge("writer_profound", "grader_profound")
    workflow.add_edge("writer_rhetorical", "grader_rhetorical")
    workflow.add_edge("writer_steady", "grader_steady")

    # --- Fan-in Edges (from Graders to Aggregator) ---
    # All three Graders must complete before Aggregator runs
    # LangGraph waits for all incoming edges before executing the node
    workflow.add_edge("grader_profound", "aggregator")
    workflow.add_edge("grader_rhetorical", "aggregator")
    workflow.add_edge("grader_steady", "aggregator")

    # --- Final Edge ---
    # Aggregator -> END: Complete the workflow
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
) -> Dict[str, Any]:
    """
    Execute the complete essay generation workflow.

    Args:
        topic: Essay topic/prompt text
        task_id: Optional database task ID for SSE events
        image_url: Optional image URL for OCR (future)

    Returns:
        Final state dictionary with all generation results
    """
    # Prepare initial state
    initial_state: EssayState = {
        "topic": topic,
        "task_id": task_id,
        "image_url": image_url,
        # Initialize empty containers for merge_dicts reducer
        "drafts": {},
        "titles": {},
        "scores": {},
        "critiques": {},
        "errors": [],
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
    BiZhen Essay Generation Workflow
    =================================

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
    ═══════╪═══════════════════════════════════════
           │         FAN-OUT (Parallel)
    ┌──────┼──────────────────┬──────────────────┐
    │      │                  │                  │
    ▼      ▼                  ▼                  ▼
┌────────────┐         ┌────────────┐      ┌────────────┐
│  WRITER    │         │  WRITER    │      │  WRITER    │
│  PROFOUND  │ (R1)    │ RHETORICAL │ (V3) │   STEADY   │ (V3)
│  深刻型    │         │  文采型    │      │  稳健型    │
└─────┬──────┘         └─────┬──────┘      └─────┬──────┘
      │                      │                   │
      ▼                      ▼                   ▼
┌────────────┐         ┌────────────┐      ┌────────────┐
│  GRADER    │         │  GRADER    │      │  GRADER    │
│  PROFOUND  │ (R1)    │ RHETORICAL │ (R1) │   STEADY   │ (R1)
│  阅卷      │         │  阅卷      │      │  阅卷      │
└─────┬──────┘         └─────┬──────┘      └─────┬──────┘
      │                      │                   │
    ═══════════════════════════════════════════════
                    FAN-IN (Merge)
                         │
                         ▼
                ┌─────────────┐
                │ AGGREGATOR  │
                │  结果汇总    │
                └──────┬──────┘
                       │
                       ▼
                    [ END ]
    """
    return diagram
