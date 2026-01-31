"""
Database initialization and seeding for BiZhen System.

This script:
1. Creates all database tables if they don't exist
2. Seeds the database with an initial admin user for first-time setup

Usage:
    python -m backend.db.init_db

As per SRS Section 3.1, this is a private system - the admin user
is created during deployment, not through public registration.
"""

import sys
from pathlib import Path

# Ensure the backend package is in the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session

from backend.db.models import Base, User, UserRole
from backend.db.session import engine, SessionLocal
from backend.core.security import get_password_hash


def create_tables() -> None:
    """Create all database tables."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")


def seed_admin_user(db: Session) -> bool:
    """
    Seed the database with an admin user.

    Returns:
        True if user was created, False if already exists
    """
    # Check if admin already exists
    existing_admin = db.query(User).filter(User.username == "admin").first()
    if existing_admin:
        print("Admin user already exists. Skipping seed.")
        return False

    # Create admin user with hashed password
    admin_user = User(
        username="admin",
        password_hash=get_password_hash("admin123"),
        role=UserRole.ADMIN,
    )

    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)

    print(f"Admin user created successfully:")
    print(f"  Username: admin")
    print(f"  Password: admin123")
    print(f"  Role: {admin_user.role.value}")
    print(f"  ID: {admin_user.id}")

    return True


def init_db() -> None:
    """
    Initialize database: create tables and seed admin user.

    This function is idempotent - safe to run multiple times.
    """
    print("=" * 50)
    print("BiZhen Database Initialization")
    print("=" * 50)

    # Step 1: Create tables
    create_tables()

    # Step 2: Seed admin user
    print("\nSeeding admin user...")
    db = SessionLocal()
    try:
        seed_admin_user(db)
    finally:
        db.close()

    print("\n" + "=" * 50)
    print("Database initialization complete!")
    print("=" * 50)


if __name__ == "__main__":
    init_db()
