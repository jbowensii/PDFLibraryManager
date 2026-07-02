"""
Database configuration and session management.

Creates a single database engine instance (singleton) and provides
a session factory for dependency injection in FastAPI endpoints.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings

# Create database engine ONCE (singleton)
# This prevents creating a new engine per request which is wasteful
if "sqlite" in settings.DATABASE_URL:
    # For SQLite testing/development
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # For production database (PostgreSQL, MySQL, etc.)
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,  # Test connections before using them
        echo=settings.DEBUG,  # Log SQL if DEBUG=True
        pool_size=20,  # Connection pool size
        max_overflow=40,  # Allow overflow connections
    )

# Create session factory bound to the singleton engine
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db():
    """
    Dependency to get database session for FastAPI endpoints.

    Yields a database session which is closed after the endpoint completes.

    Usage in endpoint:
        async def my_endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
