"""
Celery Worker for BiZhen Async Task Processing.

Implements the Consumer side of the Producer-Consumer model as
defined in HLD Section 2.2 and LLD Section 2.2.

Responsibilities:
1. Pull tasks from Redis queue
2. Execute LangGraph workflow
3. Update task status in PostgreSQL
4. Publish SSE events to Redis for real-time frontend updates
5. Persist final results to database
"""

import json
from typing import Any, Dict

from celery import Celery
import redis

from backend.config import settings
from backend.db.session import SessionLocal
from backend.db.models import Task, EssayResult, TaskStatus
from backend.core.state import ALL_STYLES


# Initialize Celery application
celery_app = Celery(
    "bizhen_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # 30 minutes max per task
    worker_prefetch_multiplier=1,  # Process one task at a time for LLM efficiency
)

# Redis client for SSE publishing
redis_client = redis.Redis.from_url(settings.redis_url)


def publish_sse(task_id: int, event_type: str, agent: str, message: str, data: Dict = None):
    """
    Publish SSE event to Redis channel for frontend consumption.

    Args:
        task_id: Database task ID
        event_type: Event type (progress/end/error)
        agent: Current agent name
        message: Human-readable message
        data: Optional additional data
    """
    channel = f"task_stream:{task_id}"
    event = {
        "type": event_type,
        "agent": agent,
        "message": message,
        "data": data or {},
    }
    try:
        redis_client.publish(channel, json.dumps(event, ensure_ascii=False))
    except Exception as e:
        print(f"Warning: Failed to publish SSE event: {e}")


@celery_app.task(bind=True, max_retries=2)
def run_generation_task(self, task_id: int) -> Dict[str, Any]:
    """
    Main Celery task for essay generation.

    This function:
    1. Loads the task from database
    2. Updates status to PROCESSING
    3. Executes the LangGraph workflow
    4. Saves results to database
    5. Updates status to COMPLETED/FAILED

    Args:
        task_id: Database task ID

    Returns:
        Dictionary with task result summary
    """
    db = SessionLocal()

    try:
        # Load task from database
        task = db.query(Task).filter(Task.id == task_id).first()

        if not task:
            return {"error": f"Task {task_id} not found"}

        # Update status to PROCESSING
        task.status = TaskStatus.PROCESSING
        db.commit()

        # Publish processing start event
        publish_sse(
            task_id=task_id,
            event_type="progress",
            agent="system",
            message="任务开始处理...",
        )

        # Import graph here to avoid circular imports
        from backend.core.graph import run_workflow

        # Execute LangGraph workflow
        # The workflow will publish SSE events internally via agents
        final_state = run_workflow(
            topic=task.input_prompt,
            task_id=task_id,
            image_url=task.image_url,
        )

        # Extract results from final state
        drafts = final_state.get("drafts", {})
        titles = final_state.get("titles", {})
        scores = final_state.get("scores", {})
        critiques = final_state.get("critiques", {})
        errors = final_state.get("errors", [])

        # Store intermediate state in task meta_info
        task.meta_info = {
            "angle": final_state.get("angle", ""),
            "thesis": final_state.get("thesis", ""),
            "outline": final_state.get("outline", {}),
            "materials": final_state.get("materials", {}),
        }

        # Save essay results to database
        essays_saved = 0
        for style in ALL_STYLES:
            content = drafts.get(style, "")
            if content:
                essay = EssayResult(
                    task_id=task_id,
                    style=style,
                    title=titles.get(style, ""),
                    content=content,
                    score=scores.get(style),
                    critique=critiques.get(style, ""),
                )
                db.add(essay)
                essays_saved += 1

        # Determine final status
        if essays_saved == 0:
            task.status = TaskStatus.FAILED
            status_message = "生成失败：未能生成任何作文"
        elif essays_saved < 3:
            task.status = TaskStatus.COMPLETED  # Partial success is still completed
            status_message = f"部分完成：生成了 {essays_saved}/3 篇作文"
        else:
            task.status = TaskStatus.COMPLETED
            avg_score = sum(scores.values()) / len(scores) if scores else 0
            status_message = f"生成完成！共 {essays_saved} 篇作文，平均分 {avg_score:.1f}"

        db.commit()

        # Publish final completion event
        publish_sse(
            task_id=task_id,
            event_type="end",
            agent="system",
            message=status_message,
            data={
                "status": task.status.value,
                "essays_count": essays_saved,
                "scores": scores,
                "errors": errors,
            },
        )

        return {
            "task_id": task_id,
            "status": task.status.value,
            "essays_saved": essays_saved,
            "scores": scores,
            "errors": errors,
        }

    except Exception as e:
        # Handle task failure
        if task:
            task.status = TaskStatus.FAILED
            db.commit()

        # Publish error event
        publish_sse(
            task_id=task_id,
            event_type="error",
            agent="system",
            message=f"任务执行失败: {str(e)}",
        )

        # Retry logic for transient errors
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)  # Retry after 60 seconds

        return {
            "task_id": task_id,
            "status": "failed",
            "error": str(e),
        }

    finally:
        db.close()


@celery_app.task
def health_check() -> Dict[str, str]:
    """
    Health check task to verify worker is running.

    Returns:
        Status dictionary
    """
    return {"status": "healthy", "worker": "bizhen_celery"}


# Optional: Task for retrying failed tasks
@celery_app.task
def retry_failed_task(task_id: int) -> Dict[str, Any]:
    """
    Retry a previously failed task.

    Args:
        task_id: Database task ID to retry

    Returns:
        Result from run_generation_task
    """
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task and task.status == TaskStatus.FAILED:
            # Reset status and delete old essays
            task.status = TaskStatus.QUEUED
            db.query(EssayResult).filter(EssayResult.task_id == task_id).delete()
            db.commit()

            # Trigger new generation
            return run_generation_task.delay(task_id)

        return {"error": "Task not found or not in failed state"}
    finally:
        db.close()
