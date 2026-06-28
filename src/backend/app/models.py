"""SQLAlchemy ORM models for the PDF Library Manager."""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    CheckConstraint,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    """User model for authentication and role-based access."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="viewer")
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    collections = relationship("Collection", back_populates="user", cascade="all, delete-orphan")
    reading_status = relationship("ReadingStatus", back_populates="user", cascade="all, delete-orphan")
    duplicate_decisions = relationship("DuplicateCandidate", foreign_keys="DuplicateCandidate.user_decision_by", back_populates="decided_by_user")

    # Constraints
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'curator', 'viewer')", name="check_valid_role"),
    )


class Book(Base):
    """Book model for PDF metadata and OCR tracking."""

    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    filesystem_path = Column(String(1024), unique=True, nullable=False, index=True)
    filename_normalized = Column(String(255), nullable=True)
    title = Column(String(500), nullable=True, index=True)
    publisher = Column(String(255), nullable=True, index=True)
    author = Column(String(255), nullable=True, index=True)
    game_name = Column(String(255), nullable=True)
    isbn = Column(String(20), nullable=True, index=True)
    product_number = Column(String(50), nullable=True)
    publication_date = Column(String(50), nullable=True)
    has_embedded_text = Column(Boolean, nullable=True)
    ocr_status = Column(String(50), nullable=False, default="pending", index=True)
    ocr_error_count = Column(Integer, nullable=False, default=0)
    ocr_language = Column(String(10), nullable=True)
    full_text_index = Column(Text, nullable=True)  # TSVECTOR for PostgreSQL
    file_size_bytes = Column(Integer, nullable=True)
    page_count = Column(Integer, nullable=True)
    ocr_engine = Column(String(50), nullable=True)
    ocr_confidence = Column(Float, nullable=True)
    cover_image_local_path = Column(String(1024), nullable=True)
    cover_image_blob = Column(String(2048), nullable=True)  # Base64 or blob reference
    metadata_source = Column(String(100), nullable=True)
    metadata_confidence = Column(Float, nullable=True)
    metadata_locked = Column(Boolean, nullable=False, default=False)
    content_hash = Column(String(64), nullable=True, unique=True)
    is_duplicate = Column(Boolean, nullable=False, default=False, index=True)
    duplicate_parent_id = Column(Integer, ForeignKey("books.id"), nullable=True)
    date_added = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    date_modified = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    date_last_scanned = Column(DateTime, nullable=True)

    # Relationships
    duplicate_children = relationship("Book", remote_side=[duplicate_parent_id], cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="book", cascade="all, delete-orphan")
    collection_books = relationship("CollectionBook", back_populates="book", cascade="all, delete-orphan")
    duplicate_candidate_1 = relationship("DuplicateCandidate", foreign_keys="DuplicateCandidate.book_id_1", back_populates="book_1")
    duplicate_candidate_2 = relationship("DuplicateCandidate", foreign_keys="DuplicateCandidate.book_id_2", back_populates="book_2")
    reading_statuses = relationship("ReadingStatus", back_populates="book", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint("metadata_confidence >= 0 AND metadata_confidence <= 1", name="check_metadata_confidence"),
        CheckConstraint("ocr_confidence >= 0 AND ocr_confidence <= 1", name="check_ocr_confidence"),
    )


class Collection(Base):
    """Collection model for organizing books by user."""

    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_shared = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="collections")
    books = relationship("CollectionBook", back_populates="collection", cascade="all, delete-orphan")


class CollectionBook(Base):
    """Association table for many-to-many relationship between collections and books."""

    __tablename__ = "collection_books"

    id = Column(Integer, primary_key=True, index=True)
    collection_id = Column(Integer, ForeignKey("collections.id"), nullable=False, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False, index=True)

    # Relationships
    collection = relationship("Collection", back_populates="books")
    book = relationship("Book", back_populates="collection_books")


class Job(Base):
    """Job model for tracking asynchronous processing tasks."""

    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_type = Column(String(100), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="queued", index=True)
    progress_percent = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    paused_at = Column(DateTime, nullable=True)

    # Relationships
    book = relationship("Book", back_populates="jobs")

    # Constraints
    __table_args__ = (
        CheckConstraint("progress_percent >= 0 AND progress_percent <= 100", name="check_progress_percent"),
    )


class DuplicateCandidate(Base):
    """Duplicate candidate model for tracking potential duplicate books."""

    __tablename__ = "duplicate_candidates"

    id = Column(Integer, primary_key=True, index=True)
    book_id_1 = Column(Integer, ForeignKey("books.id"), nullable=False, index=True)
    book_id_2 = Column(Integer, ForeignKey("books.id"), nullable=False, index=True)
    similarity_score = Column(Float, nullable=False)
    metadata_match_score = Column(Float, nullable=True)
    ocr_error_diff = Column(Integer, nullable=True)
    file_size_diff_percent = Column(Float, nullable=True)
    status = Column(String(50), nullable=False, default="pending_review", index=True)
    user_decision_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    book_1 = relationship("Book", foreign_keys=[book_id_1], back_populates="duplicate_candidate_1")
    book_2 = relationship("Book", foreign_keys=[book_id_2], back_populates="duplicate_candidate_2")
    decided_by_user = relationship("User", back_populates="duplicate_decisions")

    # Constraints
    __table_args__ = (
        CheckConstraint("similarity_score >= 0 AND similarity_score <= 1", name="check_similarity_score"),
        CheckConstraint("metadata_match_score IS NULL OR (metadata_match_score >= 0 AND metadata_match_score <= 1)", name="check_metadata_match_score"),
    )


class ReadingStatus(Base):
    """Reading status model for tracking user reading progress."""

    __tablename__ = "reading_statuses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False, index=True)
    current_page = Column(Integer, nullable=True, default=0)
    status = Column(String(50), nullable=False, default="unread")
    date_started = Column(DateTime, nullable=True)
    date_completed = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="reading_status")
    book = relationship("Book", back_populates="reading_statuses")
