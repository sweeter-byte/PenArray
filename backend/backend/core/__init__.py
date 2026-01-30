"""Core module - Business logic, agents, and LangGraph workflow."""

from .state import EssayState, merge_dicts
from .graph import create_workflow

__all__ = [
    "EssayState",
    "merge_dicts",
    "create_workflow",
]
