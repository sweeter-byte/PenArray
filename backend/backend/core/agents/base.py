"""
Base utilities for BiZhen agents.

Provides model initialization and common agent functionality.
Uses langchain-openai for DeepSeek API compatibility (OpenAI-compatible interface).

Model Strategy (per HLD Section 2.1):
- DeepSeek R1 (Reasoner): High-logic tasks (Strategist, Outliner, Writer_Profound, Graders)
- DeepSeek V3 (Chat): Creative/tool-calling tasks (Librarian, Writer_Rhetorical, Writer_Steady)
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, Callable
import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import redis
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import logging

# Configure logger
logger = logging.getLogger(__name__)

from backend.config import settings


# Redis client for SSE publishing (initialized lazily)
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """
    Get or create Redis client for SSE event publishing.

    Returns:
        Redis client instance
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(settings.redis_url)
    return _redis_client


def publish_sse_event(
    task_id: int,
    event_type: str,
    agent: str,
    message: str,
    data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Publish SSE event to Redis for real-time frontend updates.

    Args:
        task_id: Database task ID
        event_type: Event type (progress/end/error)
        agent: Name of current agent
        message: Human-readable status message
        data: Optional additional data
    """
    try:
        client = get_redis_client()
        channel = f"task_stream:{task_id}"
        event = {
            "type": event_type,
            "agent": agent,
            "message": message,
            "data": data,
        }
        client.publish(channel, json.dumps(event, ensure_ascii=False))
    except Exception as e:
        # Don't fail the workflow if SSE publishing fails
        print(f"Warning: Failed to publish SSE event: {e}")


def get_reasoner_model() -> ChatOpenAI:
    """
    Get DeepSeek R1 (Reasoner) model instance.

    Used for high-logic density tasks requiring deep reasoning:
    - Strategist: Topic analysis and angle determination
    - Outliner: Logical structure generation
    - Writer_Profound: Philosophical depth writing
    - All Graders: Fair and logical scoring

    Returns:
        ChatOpenAI instance configured for DeepSeek R1
    """
    return ChatOpenAI(
        model=settings.deepseek_reasoner_model,
        openai_api_key=settings.deepseek_api_key,
        openai_api_base=settings.deepseek_api_base,
        temperature=0.7,
        max_tokens=4096,
        max_retries=3,
        timeout=600.0,
    )


def get_chat_model() -> ChatOpenAI:
    """
    Get DeepSeek V3 (Chat) model instance.

    Used for creative generation and tool-calling tasks:
    - Librarian: RAG retrieval with tool calls
    - Writer_Rhetorical: Literary elegance
    - Writer_Steady: Reliable structured writing

    Returns:
        ChatOpenAI instance configured for DeepSeek V3
    """
    return ChatOpenAI(
        model=settings.deepseek_chat_model,
        openai_api_key=settings.deepseek_api_key,
        openai_api_base=settings.deepseek_api_base,
        temperature=0.8,
        max_tokens=4096,
        max_retries=3,
        timeout=600.0,
    )


def load_prompt(agent_name: str) -> Dict[str, Any]:
    """
    Load prompt configuration from YAML file.

    Args:
        agent_name: Name of the agent (e.g., "strategist", "writer_profound")

    Returns:
        Dictionary containing prompt configuration

    Raises:
        FileNotFoundError: If prompt file doesn't exist
    """
    prompts_dir = Path(__file__).parent.parent.parent / "prompts"
    prompt_file = prompts_dir / f"{agent_name}.yaml"

    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

    with open(prompt_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def format_prompt(template: str, **kwargs: Any) -> str:
    """
    Format a prompt template with provided variables.

    Args:
        template: Prompt template string with {placeholders}
        **kwargs: Variables to substitute into template

    Returns:
        Formatted prompt string
    """
    try:
        return template.format(**kwargs)
    except KeyError as e:
        # Return template with missing keys noted
        return template


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(Exception),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
def invoke_model(
    model: ChatOpenAI,
    system_prompt: str,
    user_prompt: str,
) -> str:
    """
    Invoke a model with system and user prompts.
    
    Wrapped with Tenacity for robust retries against transient connection errors.
    Retries 5 times with exponential backoff (4s to 10s).
    """
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    response = model.invoke(messages)
    return response.content


def create_agent_node(
    agent_name: str,
    model_type: str,
    process_fn: Callable,
) -> Callable:
    """
    Factory function to create an agent node with common boilerplate.

    Args:
        agent_name: Name for logging/SSE events
        model_type: "reasoner" or "chat"
        process_fn: Function that processes state and returns updates

    Returns:
        Node function compatible with LangGraph
    """
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        # Get task_id for SSE if available
        task_id = state.get("task_id")

        # Publish start event
        if task_id:
            publish_sse_event(
                task_id=task_id,
                event_type="progress",
                agent=agent_name,
                message=f"{agent_name} is working...",
            )

        try:
            # Get appropriate model
            model = get_reasoner_model() if model_type == "reasoner" else get_chat_model()

            # Run agent-specific logic
            result = process_fn(state, model)

            # Update current agent in state
            result["current_agent"] = agent_name

            return result

        except Exception as e:
            # Publish error event
            if task_id:
                publish_sse_event(
                    task_id=task_id,
                    event_type="error",
                    agent=agent_name,
                    message=f"{agent_name} failed: {str(e)}",
                )
            # Return error in state
            return {"errors": [f"{agent_name} failed: {str(e)}"]}

    return node
