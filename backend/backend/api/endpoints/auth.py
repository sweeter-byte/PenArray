"""
Authentication endpoints for BiZhen system.

Implements login endpoint as per HLD Section 4.1.
NOTE: No registration endpoint per SRS Section 3.1 (private system).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.api.deps import get_db, get_current_user
from backend.db.models import User
from backend.schemas.auth import LoginRequest, TokenResponse, UserResponse
from backend.core.security import (
    verify_password,
    create_access_token,
    get_token_expiry_seconds,
)


router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User Login",
    description="Authenticate with username and password to receive an access token.",
    responses={
        200: {"description": "Successfully authenticated"},
        401: {"description": "Invalid credentials"},
    },
)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """
    Authenticate user and return JWT access token.

    This is the only authentication endpoint. As per SRS Section 3.1,
    this is a private system - there is no public registration.
    Users must be created by administrators.

    Args:
        request: Login credentials (username and password)
        db: Database session

    Returns:
        TokenResponse containing JWT token and expiration info

    Raises:
        HTTPException: 401 if credentials are invalid
    """
    # Query user by username
    user = db.query(User).filter(User.username == request.username).first()

    # Verify user exists and password is correct
    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create JWT access token with user ID as subject
    access_token = create_access_token(data={"sub": str(user.id)})

    return TokenResponse(
        token=access_token,
        token_type="bearer",
        expires_in=get_token_expiry_seconds(),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Current User",
    description="Get information about the currently authenticated user.",
    responses={
        200: {"description": "Current user information"},
        401: {"description": "Not authenticated"},
    },
)
def get_me(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """
    Get current authenticated user's information.

    Args:
        current_user: User from authentication dependency

    Returns:
        UserResponse with user details (id, username, role)
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role.value,
    )
