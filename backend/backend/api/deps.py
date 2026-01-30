"""
FastAPI dependency injection functions.

Provides common dependencies for API endpoints:
- Database session management
- User authentication and authorization
"""

from typing import Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.db.session import SessionLocal
from backend.db.models import User, Token
from backend.core.security import decode_access_token


# HTTP Bearer token security scheme
security = HTTPBearer()


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency.

    Yields a database session and ensures cleanup after request.

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the currently authenticated user from JWT token.

    This dependency extracts the Bearer token from the Authorization header,
    validates it, and returns the corresponding User object.

    Args:
        credentials: HTTP Bearer credentials from request header
        db: Database session

    Returns:
        User: The authenticated user object

    Raises:
        HTTPException: 401 if token is invalid, expired, or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials

    # Decode and validate JWT token
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    # Extract user ID from token
    user_id: Optional[int] = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # Fetch user from database
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current user and verify they are active.

    Currently just returns the user, but can be extended to check
    if user account is disabled/suspended.

    Args:
        current_user: User from get_current_user dependency

    Returns:
        User: The authenticated active user

    Raises:
        HTTPException: 403 if user is inactive (future implementation)
    """
    # Future: Add check for user.is_active if needed
    return current_user


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Optionally get the current user if token is provided.

    Unlike get_current_user, this doesn't raise an error if no token
    is provided. Useful for endpoints that work both authenticated
    and unauthenticated.

    Args:
        credentials: Optional HTTP Bearer credentials
        db: Database session

    Returns:
        User if valid token provided, None otherwise
    """
    if credentials is None:
        return None

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    return db.query(User).filter(User.id == int(user_id)).first()
