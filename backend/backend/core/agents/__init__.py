"""Agent implementations for the BiZhen Multi-Agent System.

Agents:
- Strategist: Analyzes topic and determines writing angle (DeepSeek R1)
- Librarian: Retrieves relevant materials via RAG (DeepSeek V3)
- Outliner: Generates structured essay outline (DeepSeek R1)
- Writer: Generates essay drafts in three styles (R1/V3)
- Grader: Scores and critiques essays (DeepSeek R1)
- Reviser: Professional editor that applies feedback (DeepSeek R1) [NEW]
- Reviewer: Quality assurance and routing decisions (DeepSeek R1) [NEW]
- Aggregator: Collects all results for final output

Closed-Loop Revision System (NEW):
Writer -> Grader -> Reviser -> Reviewer -> (Router)
  - ACCEPT: Quality met, proceed to Aggregator
  - REVISE: Minor issues, loop back to Reviser
  - REWRITE: Major failure, loop back to Writer
"""

from .base import get_chat_model, get_reasoner_model, publish_sse_event
from .strategist import strategist_node
from .librarian import librarian_node
from .outliner import outliner_node
from .writer import writer_profound_node, writer_rhetorical_node, writer_steady_node
from .grader import (
    grader_node,
    grader_profound_node,
    grader_rhetorical_node,
    grader_steady_node,
)
from .reviser import (
    reviser_profound_node,
    reviser_rhetorical_node,
    reviser_steady_node,
)
from .reviewer import (
    reviewer_profound_node,
    reviewer_rhetorical_node,
    reviewer_steady_node,
    get_routing_decision,
)
from .aggregator import aggregator_node

__all__ = [
    # Utilities
    "get_chat_model",
    "get_reasoner_model",
    "publish_sse_event",
    # Sequential nodes
    "strategist_node",
    "librarian_node",
    "outliner_node",
    # Parallel writer nodes
    "writer_profound_node",
    "writer_rhetorical_node",
    "writer_steady_node",
    # Parallel grader nodes
    "grader_node",
    "grader_profound_node",
    "grader_rhetorical_node",
    "grader_steady_node",
    # Parallel reviser nodes (NEW)
    "reviser_profound_node",
    "reviser_rhetorical_node",
    "reviser_steady_node",
    # Parallel reviewer nodes (NEW)
    "reviewer_profound_node",
    "reviewer_rhetorical_node",
    "reviewer_steady_node",
    "get_routing_decision",
    # Aggregator
    "aggregator_node",
]
