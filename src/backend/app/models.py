"""
SQLAlchemy ORM models for PDF Library Manager.

Defines the database schema for books and duplicate tracking.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    """Represents a user in the system."""

    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default='curator')  # admin, curator, viewer
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


class Book(Base):
    """Represents a book in the library."""

    __tablename__ = 'books'

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    author = Column(String(255), nullable=False, default='')
    publisher = Column(String(255), nullable=False, default='')
    isbn = Column(String(20), nullable=True)
    content_hash = Column(String(64), nullable=True)
    ocr_error_count = Column(Integer, default=0)
    is_duplicate = Column(Boolean, default=False)
    duplicate_parent_id = Column(Integer, ForeignKey('books.id'), nullable=True)
    filesystem_path = Column(String(512), nullable=True, unique=True)
    filename_normalized = Column(String(255), nullable=True)
    ocr_status = Column(String(50), default='pending')  # pending, in_progress, completed, failed
    has_embedded_text = Column(Boolean, default=False)
    file_size_bytes = Column(Integer, nullable=True)
    full_text_index = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Book(id={self.id}, title='{self.title}', author='{self.author}')>"


class Job(Base):
    """Represents a processing job for a book."""

    __tablename__ = 'jobs'

    id = Column(Integer, primary_key=True)
    book_id = Column(Integer, ForeignKey('books.id'), nullable=False)
    job_type = Column(String(50), nullable=False)  # ocr, dedup, metadata_lookup
    status = Column(String(50), default='queued')  # queued, in_progress, completed, failed, paused, cancelled
    progress_percent = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    paused_at = Column(DateTime, nullable=True)
    celery_task_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Job(id={self.id}, book_id={self.book_id}, type='{self.job_type}', status='{self.status}')>"


class DuplicateCandidate(Base):
    """Represents a potential duplicate pair of books."""

    __tablename__ = 'duplicate_candidates'

    id = Column(Integer, primary_key=True)
    book_id_1 = Column(Integer, ForeignKey('books.id'), nullable=False)
    book_id_2 = Column(Integer, ForeignKey('books.id'), nullable=False)
    similarity_score = Column(Float, nullable=False)
    status = Column(String(50), default='pending')
    # Status values:
    # - 'pending': Low confidence (score < 0.75), awaiting user review
    # - 'manual_review': Medium confidence with <20% quality diff
    # - 'resolved_keep_1': Auto-resolved, keeping book 1
    # - 'resolved_keep_2': Auto-resolved, keeping book 2
    user_decision_by = Column(Integer, nullable=True)  # User ID
    resolved_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return (
            f"<DuplicateCandidate(id={self.id}, "
            f"book_id_1={self.book_id_1}, book_id_2={self.book_id_2}, "
            f"score={self.similarity_score}, status='{self.status}')>"
        )


class Collection(Base):
    """Represents a user's collection of books."""

    __tablename__ = 'collections'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Collection(id={self.id}, user_id={self.user_id}, name='{self.name}')>"


class CollectionBook(Base):
    """Junction table for collection-book relationships."""

    __tablename__ = 'collection_books'

    id = Column(Integer, primary_key=True)
    collection_id = Column(Integer, ForeignKey('collections.id'), nullable=False)
    book_id = Column(Integer, ForeignKey('books.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<CollectionBook(collection_id={self.collection_id}, book_id={self.book_id})>"


class AuditLog(Base):
    """Represents an audit log entry for system actions."""

    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    action = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', user_id={self.user_id})>"
