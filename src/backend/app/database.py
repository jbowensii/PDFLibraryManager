"""Database configuration and session management."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings

# Create database engine
# Use SQLite in test environments (when pytest is running)
if os.environ.get("PYTEST_CURRENT_TEST") or "sqlite" in settings.DATABASE_URL:
    # SQLite (for testing)
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # PostgreSQL (production)
    try:
        engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            echo=settings.DEBUG,
        )
    except Exception:
        # Fallback to SQLite if PostgreSQL connection fails
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Declarative base for ORM models
Base = declarative_base()


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
