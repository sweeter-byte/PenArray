"""API module - FastAPI routers and endpoints."""

from fastapi import APIRouter
from .endpoints import auth, task, export

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(task.router, prefix="/task", tags=["Tasks"])
api_router.include_router(export.router, prefix="/export", tags=["Export"])

__all__ = ["api_router"]
