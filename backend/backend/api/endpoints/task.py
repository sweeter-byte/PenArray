"""
Task management endpoints for BiZhen system.

Implements task creation, result retrieval, and SSE streaming
as per HLD Section 4.2 and LLD Section 2.3.
"""

import json
import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import redis.asyncio as aioredis

from backend.api.deps import get_db, get_current_user
from backend.core.security import decode_access_token
from backend.db.models import User, Task, EssayResult, TaskStatus
from backend.schemas.task import (
    TaskCreateRequest,
    TaskCreateResponse,
    TaskResponse,
    EssayResponse,
)
from backend.config import settings


router = APIRouter()


@router.post(
    "/create",
    response_model=TaskCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Generation Task",
    description="Create a new essay generation task. Returns immediately with task ID.",
    responses={
        201: {"description": "Task created and queued"},
        401: {"description": "Not authenticated"},
    },
)
def create_task(
    request: TaskCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskCreateResponse:
    """
    Create a new essay generation task (Producer).

    This endpoint implements the Producer side of the Producer-Consumer model:
    1. Creates a Task record in PostgreSQL with status=QUEUED
    2. Dispatches the task to Celery worker via Redis
    3. Returns immediately with task_id for client polling/SSE

    Args:
        request: Task creation request with prompt and optional image URL
        db: Database session
        current_user: Authenticated user

    Returns:
        TaskCreateResponse with task_id and initial status
    """
    # Create task record in database
    # Store custom_structure in meta_info for later use by the worker
    meta_info = {}
    if request.custom_structure:
        meta_info["custom_structure"] = request.custom_structure

    task = Task(
        user_id=current_user.id,
        input_prompt=request.prompt,
        image_url=request.image_url,
        status=TaskStatus.QUEUED,
        meta_info=meta_info if meta_info else None,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Dispatch to Celery worker (import here to avoid circular imports)
    # The actual Celery task will be implemented in Phase 3
    try:
        from backend.worker import run_generation_task
        run_generation_task.delay(task.id)
    except ImportError:
        # Worker not yet implemented, task will stay queued
        pass

    return TaskCreateResponse(
        task_id=task.id,
        status=task.status.value,
    )


@router.get(
    "/{task_id}/result",
    response_model=TaskResponse,
    summary="Get Task Result",
    description="Get the final result of a generation task including all essays.",
    responses={
        200: {"description": "Task result with essays"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this task"},
        404: {"description": "Task not found"},
    },
)
def get_task_result(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    """
    Get the result of a generation task.

    Returns the task metadata and all generated essays.
    Users can only access their own tasks.

    Args:
        task_id: The task ID to retrieve
        db: Database session
        current_user: Authenticated user

    Returns:
        TaskResponse with task info and list of essays

    Raises:
        HTTPException: 404 if task not found, 403 if not authorized
    """
    # Query task with eager loading of essays
    task = db.query(Task).filter(Task.id == task_id).first()

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    # Authorization check: users can only access their own tasks
    if task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this task",
        )

    # Build response with essays
    essays = [
        EssayResponse(
            id=essay.id,
            style=essay.style,
            title=essay.title,
            content=essay.content,
            score=essay.score,
            critique=essay.critique,
        )
        for essay in task.essays
    ]

    return TaskResponse(
        task_id=task.id,
        status=task.status.value,
        created_at=task.created_at,
        updated_at=task.updated_at,
        input_prompt=task.input_prompt,
        essays=essays,
    )


@router.get(
    "/{task_id}/stream",
    summary="Stream Task Progress",
    description="Server-Sent Events stream for real-time task progress updates.",
    responses={
        200: {"description": "SSE stream of progress events"},
        401: {"description": "Not authenticated"},
        404: {"description": "Task not found"},
    },
)
async def stream_task_progress(
    task_id: int,
    token: str = Query(..., description="JWT authentication token"),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    Stream task progress via Server-Sent Events (SSE).

    Implements the streaming response as per LLD Section 2.3:
    - Subscribes to Redis Pub/Sub channel for task updates
    - Streams progress events to client in real-time
    - Closes connection on task completion or error

    Note: Uses query parameter for token since EventSource API
    does not support custom headers.

    Args:
        task_id: The task ID to stream progress for
        token: JWT authentication token (query parameter)
        db: Database session

    Returns:
        StreamingResponse with SSE content type
    """
    # Manual token validation (EventSource doesn't support headers)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception

    # Verify task exists and user has access
    task = db.query(Task).filter(Task.id == task_id).first()

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    if task.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this task",
        )

    async def event_generator() -> AsyncGenerator[str, None]:
        """
        Generate SSE events from Redis Pub/Sub.

        Subscribes to task-specific channel and yields events
        until completion or error signal is received.
        """
        redis = aioredis.from_url(settings.redis_url)
        pubsub = redis.pubsub()
        channel = f"task_stream:{task_id}"

        try:
            await pubsub.subscribe(channel)

            # Send initial connection event
            yield f"data: {json.dumps({'type': 'connected', 'task_id': task_id})}\n\n"

            # Check if task is already completed
            if task.status == TaskStatus.COMPLETED:
                yield f"data: {json.dumps({'type': 'end', 'status': 'completed'})}\n\n"
                return
            elif task.status == TaskStatus.FAILED:
                yield f"data: {json.dumps({'type': 'end', 'status': 'failed'})}\n\n"
                return

            # Listen for messages with timeout
            while True:
                try:
                    message = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                        timeout=60.0  # 60 second timeout for long-running tasks
                    )

                    if message is not None and message["type"] == "message":
                        data = message["data"]
                        if isinstance(data, bytes):
                            data = data.decode("utf-8")

                        yield f"data: {data}\n\n"

                        # Check for end signal
                        try:
                            parsed = json.loads(data)
                            if parsed.get("type") in ("end", "error"):
                                break
                        except json.JSONDecodeError:
                            pass

                except asyncio.TimeoutError:
                    # Send keepalive ping
                    yield f": keepalive\n\n"

        finally:
            await pubsub.unsubscribe(channel)
            await redis.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get(
    "/{task_id}/status",
    summary="Get Task Status",
    description="Get the current status of a task without full result.",
    responses={
        200: {"description": "Task status"},
        401: {"description": "Not authenticated"},
        404: {"description": "Task not found"},
    },
)
def get_task_status(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get quick status check for a task.

    Lightweight endpoint for polling task status without
    loading full essay content.

    Args:
        task_id: The task ID to check
        db: Database session
        current_user: Authenticated user

    Returns:
        Dict with task_id and current status
    """
    task = db.query(Task).filter(Task.id == task_id).first()

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    if task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this task",
        )

    return {
        "task_id": task.id,
        "status": task.status.value,
    }
