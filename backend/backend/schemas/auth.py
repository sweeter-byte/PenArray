"""
Pydantic schemas for authentication endpoints.

Defines request/response models for login and token operations.
No registration schemas as per SRS Section 3.1 (private system).
"""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """
    Login request schema.

    Used for POST /api/auth/login endpoint.
    """
    username: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Username for authentication"
    )
    password: str = Field(
        ...,
        min_length=1,
        description="Password for authentication"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "teacher_wang",
                "password": "secure_password"
            }
        }
    }


class TokenResponse(BaseModel):
    """
    Token response schema.

    Returned after successful authentication.
    """
    token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")

    model_config = {
        "json_schema_extra": {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 86400
            }
        }
    }


class UserResponse(BaseModel):
    """
    User information response schema.

    Used for returning user details (excludes sensitive data).
    """
    id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    role: str = Field(..., description="User role (admin/user)")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "username": "teacher_wang",
                "role": "user"
            }
        }
    }
