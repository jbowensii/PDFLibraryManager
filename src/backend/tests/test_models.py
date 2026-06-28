"""Tests for ORM models."""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import User, Book, Collection, Job, DuplicateCandidate


@pytest.fixture(scope="function")
def db():
    """Create a fresh in-memory SQLite database for each test."""
    # Use SQLite for testing
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = TestSessionLocal()
    yield db_session
    db_session.close()
    Base.metadata.drop_all(bind=engine)


class TestUserCreation:
    """Test user model creation and retrieval."""

    def test_user_creation(self, db):
        """Create a user, fetch by username, verify fields, cleanup."""
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password_123",
            role="curator",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.password_hash == "hashed_password_123"
        assert user.role == "curator"
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)

        # Test fetch by username
        fetched = db.query(User).filter(User.username == "testuser").first()
        assert fetched is not None
        assert fetched.id == user.id

        # Cleanup
        db.delete(user)
        db.commit()

        # Verify deletion
        assert db.query(User).filter(User.username == "testuser").first() is None


class TestBookCreation:
    """Test book model creation and indexed fields."""

    def test_book_creation(self, db):
        """Create book with metadata, verify indexed fields work."""
        book = Book(
            filesystem_path="/library/Publisher/Game/Book Title - 978-0-123456-78-9.pdf",
            filename_normalized="book_title.pdf",
            title="Book Title",
            publisher="Test Publisher",
            author="Test Author",
            game_name="Test Game",
            isbn="978-0-123456-78-9",
            product_number="PROD123",
            publication_date="2023-06-28",
            has_embedded_text=True,
            ocr_status="pending",
            ocr_error_count=0,
            ocr_language="eng",
            file_size_bytes=1024000,
            page_count=300,
            ocr_engine="tesseract",
            ocr_confidence=0.85,
            metadata_source="google_books",
            metadata_confidence=0.92,
            metadata_locked=False,
            content_hash="abc123def456",
            is_duplicate=False,
        )
        db.add(book)
        db.commit()
        db.refresh(book)

        assert book.id is not None
        assert book.title == "Book Title"
        assert book.author == "Test Author"
        assert book.publisher == "Test Publisher"
        assert book.isbn == "978-0-123456-78-9"
        assert book.ocr_status == "pending"
        assert book.metadata_confidence == 0.92
        assert book.file_size_bytes == 1024000
        assert book.page_count == 300

        # Test indexed fields can be queried
        assert db.query(Book).filter(Book.title == "Book Title").first() is not None
        assert db.query(Book).filter(Book.author == "Test Author").first() is not None
        assert db.query(Book).filter(Book.publisher == "Test Publisher").first() is not None
        assert db.query(Book).filter(Book.isbn == "978-0-123456-78-9").first() is not None
        assert db.query(Book).filter(Book.ocr_status == "pending").first() is not None
        assert db.query(Book).filter(Book.is_duplicate == False).first() is not None

        # Cleanup
        db.delete(book)
        db.commit()


class TestCollectionCreation:
    """Test collection model creation linked to user."""

    def test_collection_creation(self, db):
        """Create collection linked to user."""
        user = User(
            username="collectionuser",
            email="coll@example.com",
            password_hash="hashed",
            role="viewer",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        collection = Collection(
            user_id=user.id,
            name="My Collection",
            description="A test collection",
            is_shared=False,
        )
        db.add(collection)
        db.commit()
        db.refresh(collection)

        assert collection.id is not None
        assert collection.user_id == user.id
        assert collection.name == "My Collection"
        assert collection.description == "A test collection"
        assert collection.is_shared is False
        assert isinstance(collection.created_at, datetime)

        # Verify relationship
        assert collection.user.username == "collectionuser"

        # Cleanup
        db.delete(collection)
        db.delete(user)
        db.commit()


class TestJobCreation:
    """Test job model creation with status tracking."""

    def test_job_creation(self, db):
        """Create job with status transitions."""
        book = Book(
            filesystem_path="/library/test.pdf",
            filename_normalized="test.pdf",
            title="Test Book",
            ocr_status="pending",
        )
        db.add(book)
        db.commit()
        db.refresh(book)

        job = Job(
            job_type="ocr",
            book_id=book.id,
            status="queued",
            progress_percent=0,
            retry_count=0,
            max_retries=3,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        assert job.id is not None
        assert job.job_type == "ocr"
        assert job.book_id == book.id
        assert job.status == "queued"
        assert job.progress_percent == 0
        assert job.retry_count == 0
        assert job.max_retries == 3
        assert isinstance(job.created_at, datetime)

        # Test status query
        assert db.query(Job).filter(Job.status == "queued").first() is not None

        # Cleanup
        db.delete(job)
        db.delete(book)
        db.commit()


class TestDuplicateCandidateCreation:
    """Test duplicate candidate model creation."""

    def test_duplicate_candidate_creation(self, db):
        """Create candidate pair, verify scoring fields."""
        book1 = Book(
            filesystem_path="/library/book1.pdf",
            filename_normalized="book1.pdf",
            title="Book Title",
            author="Author Name",
        )
        book2 = Book(
            filesystem_path="/library/book2.pdf",
            filename_normalized="book2.pdf",
            title="Book Title",
            author="Author Name",
        )
        db.add_all([book1, book2])
        db.commit()
        db.refresh(book1)
        db.refresh(book2)

        user = User(
            username="curator",
            email="curator@example.com",
            password_hash="hashed",
            role="curator",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        candidate = DuplicateCandidate(
            book_id_1=book1.id,
            book_id_2=book2.id,
            similarity_score=0.95,
            metadata_match_score=0.98,
            ocr_error_diff=2,
            file_size_diff_percent=0.5,
            status="pending_review",
            user_decision_by=user.id,
            notes="Very similar content and metadata",
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)

        assert candidate.id is not None
        assert candidate.book_id_1 == book1.id
        assert candidate.book_id_2 == book2.id
        assert candidate.similarity_score == 0.95
        assert candidate.metadata_match_score == 0.98
        assert candidate.ocr_error_diff == 2
        assert candidate.file_size_diff_percent == 0.5
        assert candidate.status == "pending_review"
        assert isinstance(candidate.created_at, datetime)

        # Test status query
        assert db.query(DuplicateCandidate).filter(
            DuplicateCandidate.status == "pending_review"
        ).first() is not None

        # Cleanup
        db.delete(candidate)
        db.delete(user)
        db.delete(book1)
        db.delete(book2)
        db.commit()
