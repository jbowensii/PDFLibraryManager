"""
Pytest configuration for backend tests.
"""

import sys
from pathlib import Path
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.models import Base
from app.database import get_db
from app.main import app

# Use in-memory SQLite for tests with StaticPool to keep connection alive
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables once at module load
Base.metadata.create_all(bind=engine)


def override_get_db():
    """Override dependency for tests."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Apply dependency override before app initialization
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function", autouse=True)
def cleanup_db():
    """Clean database between tests."""
    # Before test: no action needed (tables are empty from previous test)
    yield
    # After test: clear all tables
    db = TestingSessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(text(f"DELETE FROM {table.name}"))
        db.commit()
    finally:
        db.close()
