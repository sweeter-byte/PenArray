"""
Database session management for BiZhen system.

Provides SQLAlchemy engine and session factory for database operations.
Uses connection pooling for efficient resource management.
"""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.config import settings


# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    settings.db_url,
    pool_pre_ping=True,  # Enable connection health checks
    pool_size=10,        # Maximum number of connections in the pool
    max_overflow=20,     # Maximum overflow connections
    echo=settings.debug,  # Log SQL statements in debug mode
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.

    Yields a database session and ensures proper cleanup after use.
    Use with FastAPI's Depends() for automatic session management.

    Yields:
        Session: SQLAlchemy database session

    Example:
        @router.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database tables.

    Creates all tables defined in the models if they don't exist.
    Should be called on application startup.
    """
    from backend.db.models import Base
    Base.metadata.create_all(bind=engine)
