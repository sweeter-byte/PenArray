"""
SQLAlchemy ORM Models for BiZhen System.

Implements the data models exactly as defined in LLD Section 1.1:
- User: System users with role-based access
- Token: Access tokens for authentication
- Task: Essay generation tasks
- EssayResult: Generated essays with scores and critiques

Note: UserRole and TaskStatus are implemented as Python Enums
that map to database enum types for type safety.
"""

from datetime import datetime
import enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime,
    Boolean,
    JSON,
    Enum as SAEnum,
)
from sqlalchemy.orm import relationship, declarative_base


# Base class for all models
Base = declarative_base()


class UserRole(str, enum.Enum):
    """
    User role enumeration.

    - ADMIN: System administrator with full access, can issue tokens
    - USER: Regular user with token-based access to generation features
    """
    ADMIN = "admin"
    USER = "user"


class TaskStatus(str, enum.Enum):
    """
    Task status enumeration for tracking generation workflow.

    - QUEUED: Task created and waiting in queue
    - PROCESSING: Task picked up by worker, agents executing
    - COMPLETED: All essays generated successfully
    - FAILED: Task failed due to error
    """
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    """
    User model for authentication and authorization.

    As per SRS Section 3.1, this is a private system - users are created
    by administrators only, no public registration.

    Attributes:
        id: Primary key
        username: Unique username for login
        password_hash: Bcrypt hashed password
        role: UserRole enum (admin/user)
        created_at: Account creation timestamp

    Relationships:
        tokens: One-to-many with Token
        tasks: One-to-many with Task
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.USER, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    tokens = relationship("Token", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', role={self.role.value})>"


class Token(Base):
    """
    Access token model for API authentication.

    Tokens are issued by administrators and have expiration dates.
    Used for Bearer token authentication in API requests.

    Attributes:
        id: Primary key
        user_id: Foreign key to users table
        access_token: Unique token string (64 chars)
        expires_at: Token expiration timestamp
        is_active: Whether token is currently valid

    Relationships:
        user: Many-to-one with User
    """
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    access_token = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="tokens")

    def __repr__(self) -> str:
        return f"<Token(id={self.id}, user_id={self.user_id}, is_active={self.is_active})>"

    @property
    def is_expired(self) -> bool:
        """Check if token has expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if token is both active and not expired."""
        return self.is_active and not self.is_expired


class Task(Base):
    """
    Essay generation task model.

    Represents a single essay generation request that goes through
    the multi-agent workflow (Strategist -> Librarian -> Outliner -> Writers -> Graders).

    Attributes:
        id: Primary key
        user_id: Foreign key to users table
        input_prompt: The essay topic/prompt text
        image_url: Optional URL to topic image (for OCR processing)
        status: TaskStatus enum tracking workflow progress
        meta_info: JSON field storing intermediate data (outline, strategy, etc.)
        created_at: Task creation timestamp
        updated_at: Last update timestamp

    Relationships:
        user: Many-to-one with User
        essays: One-to-many with EssayResult
    """
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    input_prompt = Column(Text, nullable=False)
    image_url = Column(String(255), nullable=True)
    status = Column(SAEnum(TaskStatus), default=TaskStatus.QUEUED, nullable=False)
    # JSON field for storing intermediate agent outputs (angle, materials, outline, etc.)
    # Uses JSONB on PostgreSQL for efficient querying
    meta_info = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="tasks")
    essays = relationship("EssayResult", back_populates="task", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, status={self.status.value}, user_id={self.user_id})>"


class EssayResult(Base):
    """
    Generated essay result model.

    Stores the final output from each Writer agent, along with
    the Grader agent's score and critique.

    Each Task generates exactly 3 essays (profound, rhetorical, steady).

    Attributes:
        id: Primary key
        task_id: Foreign key to tasks table
        style: Essay style ('profound', 'rhetorical', 'steady')
        title: Generated essay title
        content: Full essay text content
        score: Grader's score (0-60, following Gaokao standards)
        critique: Grader's detailed feedback and comments

    Relationships:
        task: Many-to-one with Task
    """
    __tablename__ = "essays"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    style = Column(String(20), nullable=False)  # 'profound', 'rhetorical', 'steady'
    title = Column(String(100), nullable=True)
    content = Column(Text, nullable=False)
    score = Column(Integer, nullable=True)  # 0-60 based on Gaokao grading
    critique = Column(Text, nullable=True)

    # Relationships
    task = relationship("Task", back_populates="essays")

    def __repr__(self) -> str:
        return f"<EssayResult(id={self.id}, task_id={self.task_id}, style='{self.style}', score={self.score})>"
