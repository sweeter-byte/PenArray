"""
Pydantic schemas for task and essay endpoints.

Defines request/response models as specified in LLD Section 1.2.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class TaskCreateRequest(BaseModel):
    """
    Task creation request schema.

    Used for POST /api/task/create endpoint.
    Supports both text prompts and optional image URLs (for OCR).
    Also supports custom structure constraints for advanced users.
    """
    prompt: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Essay topic or prompt text"
    )
    image_url: Optional[str] = Field(
        None,
        max_length=255,
        description="Optional URL to topic image for OCR processing"
    )
    custom_structure: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional custom structure constraints for essay generation"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "prompt": "阅读下面的材料，根据要求写作。'躺平'与'内卷'成为当代青年热议的话题...",
                "image_url": None,
                "custom_structure": None
            }
        }
    }


class TaskCreateResponse(BaseModel):
    """
    Task creation response schema.

    Returned immediately after task is queued.
    """
    task_id: int = Field(..., description="Unique task identifier")
    status: str = Field(..., description="Initial task status (queued)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "task_id": 1024,
                "status": "queued"
            }
        }
    }


class EssayResponse(BaseModel):
    """
    Individual essay response schema.

    Represents a single generated essay with its score and critique.
    """
    id: int = Field(..., description="Essay ID")
    style: str = Field(..., description="Essay style: profound/rhetorical/steady")
    title: Optional[str] = Field(None, description="Essay title")
    content: str = Field(..., description="Full essay content")
    score: Optional[int] = Field(None, ge=0, le=60, description="Grader score (0-60)")
    critique: Optional[str] = Field(None, description="Grader's detailed feedback")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "style": "profound",
                "title": "在躺平与内卷之间寻找第三条路",
                "content": "当'躺平'与'内卷'成为当代青年的两难抉择...",
                "score": 54,
                "critique": "立意深刻，论证有力。建议加强结尾升华..."
            }
        }
    }


class TaskResponse(BaseModel):
    """
    Complete task response schema.

    Used for GET /api/task/{id}/result endpoint.
    Includes task metadata and all generated essays.
    """
    task_id: int = Field(..., description="Task ID")
    status: str = Field(..., description="Current task status")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    input_prompt: Optional[str] = Field(None, description="Original input prompt")
    essays: List[EssayResponse] = Field(
        default_factory=list,
        description="List of generated essays"
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "task_id": 1024,
                "status": "completed",
                "created_at": "2026-01-30T10:30:00",
                "updated_at": "2026-01-30T10:33:45",
                "input_prompt": "关于'躺平'与'内卷'的辩证思考",
                "essays": []
            }
        }
    }


class StreamEvent(BaseModel):
    """
    SSE stream event schema.

    Used for real-time progress updates via GET /api/task/{id}/stream.
    """
    type: str = Field(..., description="Event type: progress/end/error")
    agent: Optional[str] = Field(None, description="Current active agent name")
    message: Optional[str] = Field(None, description="Status message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional event data")

    model_config = {
        "json_schema_extra": {
            "example": {
                "type": "progress",
                "agent": "strategist",
                "message": "正在分析题目切入点...",
                "data": None
            }
        }
    }
