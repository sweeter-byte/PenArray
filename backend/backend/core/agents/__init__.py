"""Agent implementations for the BiZhen Multi-Agent System.

Agents:
- Strategist: Analyzes topic and determines writing angle (DeepSeek R1)
- Librarian: Retrieves relevant materials via RAG (DeepSeek V3)
- Outliner: Generates structured essay outline (DeepSeek R1)
- Writer: Generates essay drafts in three styles (R1/V3)
- Grader: Scores and critiques essays (DeepSeek R1)
- Aggregator: Collects all results for final output
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
    # Aggregator
    "aggregator_node",
]
