#!/usr/bin/env python3
"""
Database verification script for BiZhen system.

This script verifies that:
1. Database connection is working
2. All tables are created correctly
3. Model relationships are properly configured
4. Enums are correctly defined

Run this script after setting up the database to verify the schema.

Usage:
    python check_db.py [--create-test-user]

Options:
    --create-test-user  Create a test admin user for development
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from backend.config import settings
from backend.db.session import engine, SessionLocal, init_db
from backend.db.models import Base, User, Token, Task, EssayResult, UserRole, TaskStatus
from backend.core.security import get_password_hash


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def check_connection() -> bool:
    """Verify database connection is working."""
    print_header("Database Connection Check")

    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print(f"  [OK] Connected to database")
            print(f"  [OK] Database URL: {settings.db_url.split('@')[1] if '@' in settings.db_url else 'localhost'}")
            return True
    except Exception as e:
        print(f"  [FAIL] Connection failed: {e}")
        return False


def check_tables() -> bool:
    """Verify all required tables exist."""
    print_header("Table Existence Check")

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    required_tables = ["users", "tokens", "tasks", "essays"]
    all_exist = True

    for table in required_tables:
        if table in existing_tables:
            print(f"  [OK] Table '{table}' exists")
        else:
            print(f"  [FAIL] Table '{table}' is MISSING")
            all_exist = False

    return all_exist


def check_columns() -> bool:
    """Verify table columns match the model definitions."""
    print_header("Column Verification")

    inspector = inspect(engine)
    all_correct = True

    # Expected columns for each table
    expected_columns = {
        "users": ["id", "username", "password_hash", "role", "created_at"],
        "tokens": ["id", "user_id", "access_token", "expires_at", "is_active"],
        "tasks": ["id", "user_id", "input_prompt", "image_url", "status", "meta_info", "created_at", "updated_at"],
        "essays": ["id", "task_id", "style", "title", "content", "score", "critique"],
    }

    for table_name, expected_cols in expected_columns.items():
        try:
            columns = [col["name"] for col in inspector.get_columns(table_name)]
            missing = set(expected_cols) - set(columns)
            extra = set(columns) - set(expected_cols)

            if not missing:
                print(f"  [OK] Table '{table_name}' has all required columns")
            else:
                print(f"  [FAIL] Table '{table_name}' missing columns: {missing}")
                all_correct = False

            if extra:
                print(f"  [INFO] Table '{table_name}' has extra columns: {extra}")

        except Exception as e:
            print(f"  [FAIL] Could not inspect table '{table_name}': {e}")
            all_correct = False

    return all_correct


def check_enums() -> bool:
    """Verify enum values are correctly defined."""
    print_header("Enum Verification")

    all_correct = True

    # Check UserRole enum
    expected_user_roles = {"admin", "user"}
    actual_user_roles = {role.value for role in UserRole}
    if actual_user_roles == expected_user_roles:
        print(f"  [OK] UserRole enum values: {actual_user_roles}")
    else:
        print(f"  [FAIL] UserRole mismatch. Expected: {expected_user_roles}, Got: {actual_user_roles}")
        all_correct = False

    # Check TaskStatus enum
    expected_task_statuses = {"queued", "processing", "completed", "failed"}
    actual_task_statuses = {status.value for status in TaskStatus}
    if actual_task_statuses == expected_task_statuses:
        print(f"  [OK] TaskStatus enum values: {actual_task_statuses}")
    else:
        print(f"  [FAIL] TaskStatus mismatch. Expected: {expected_task_statuses}, Got: {actual_task_statuses}")
        all_correct = False

    return all_correct


def check_relationships(db: Session) -> bool:
    """Verify model relationships are working."""
    print_header("Relationship Verification")

    all_correct = True

    try:
        # Test User -> Tasks relationship
        user = db.query(User).first()
        if user:
            _ = user.tasks  # Access relationship
            _ = user.tokens
            print(f"  [OK] User relationships (tasks, tokens) accessible")
        else:
            print(f"  [INFO] No users in database to test relationships")

        # Test Task -> Essays relationship
        task = db.query(Task).first()
        if task:
            _ = task.essays
            _ = task.user
            print(f"  [OK] Task relationships (essays, user) accessible")
        else:
            print(f"  [INFO] No tasks in database to test relationships")

        # Model instantiation test
        test_user = User(username="test", password_hash="test", role=UserRole.USER)
        test_task = Task(user_id=1, input_prompt="test", status=TaskStatus.QUEUED)
        test_essay = EssayResult(task_id=1, style="profound", content="test")
        print(f"  [OK] Model instantiation successful")

    except Exception as e:
        print(f"  [FAIL] Relationship check failed: {e}")
        all_correct = False

    return all_correct


def create_test_user(db: Session) -> None:
    """Create a test admin user for development."""
    print_header("Creating Test User")

    # Check if test user already exists
    existing = db.query(User).filter(User.username == "admin").first()
    if existing:
        print(f"  [INFO] Test user 'admin' already exists (id={existing.id})")
        return

    # Create test admin user
    admin_user = User(
        username="admin",
        password_hash=get_password_hash("admin123"),
        role=UserRole.ADMIN,
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)

    print(f"  [OK] Created test admin user:")
    print(f"       Username: admin")
    print(f"       Password: admin123")
    print(f"       Role: admin")
    print(f"       ID: {admin_user.id}")


def main() -> int:
    """Run all database verification checks."""
    print("\n" + "=" * 60)
    print("  BiZhen Database Verification Script")
    print("=" * 60)

    # Initialize database tables
    print("\nInitializing database tables...")
    try:
        init_db()
        print("  [OK] Database tables initialized")
    except Exception as e:
        print(f"  [FAIL] Failed to initialize tables: {e}")
        return 1

    # Run checks
    results = []
    results.append(("Connection", check_connection()))
    results.append(("Tables", check_tables()))
    results.append(("Columns", check_columns()))
    results.append(("Enums", check_enums()))

    db = SessionLocal()
    try:
        results.append(("Relationships", check_relationships(db)))

        # Create test user if requested
        if "--create-test-user" in sys.argv:
            create_test_user(db)

    finally:
        db.close()

    # Summary
    print_header("Verification Summary")
    all_passed = True
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n  All checks passed! Database is ready.")
        return 0
    else:
        print("\n  Some checks failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
