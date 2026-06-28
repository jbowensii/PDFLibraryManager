"""Tests for book API endpoints."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import create_app
from app.models import User, Book
from app.auth.password import hash_password
from app.auth.jwt_handler import create_access_token


@pytest.fixture(scope="function")
def db():
    """Create a fresh in-memory SQLite database for each test."""
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


@pytest.fixture
def client(db):
    """Create a test client with test database session."""

    def override_get_db():
        yield db

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture
def viewer_user(db):
    """Create a viewer user for testing."""
    user = User(
        username="viewer_user",
        email="viewer@example.com",
        password_hash=hash_password("viewerpass123"),
        role="viewer",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def curator_user(db):
    """Create a curator user for testing."""
    user = User(
        username="curator_user",
        email="curator@example.com",
        password_hash=hash_password("curatorpass123"),
        role="curator",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_user(db):
    """Create an admin user for testing."""
    user = User(
        username="admin_user",
        email="admin@example.com",
        password_hash=hash_password("adminpass123"),
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_book(db):
    """Create a sample book for testing."""
    book = Book(
        filesystem_path="/path/to/book.pdf",
        title="Sample Book",
        author="John Doe",
        publisher="Test Publisher",
        isbn="1234567890",
        is_duplicate=False,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


class TestListBooksEndpoint:
    """Test the GET /books endpoint."""

    def test_list_books_success(self, client, viewer_user, sample_book):
        """List books successfully with authentication."""
        token = create_access_token(viewer_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/v1/books/", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert "pages" in data
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Sample Book"

    def test_list_books_pagination_first_page(self, client, viewer_user, db):
        """Test pagination on first page."""
        # Create 50 books
        for i in range(50):
            book = Book(
                filesystem_path=f"/path/to/book{i}.pdf",
                title=f"Book {i}",
                author="Author",
                is_duplicate=False,
            )
            db.add(book)
        db.commit()

        token = create_access_token(viewer_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/v1/books/?page=1&limit=20", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["limit"] == 20
        assert data["total"] == 50
        assert data["pages"] == 3
        assert len(data["items"]) == 20

    def test_list_books_pagination_second_page(self, client, viewer_user, db):
        """Test pagination on second page."""
        # Create 50 books
        for i in range(50):
            book = Book(
                filesystem_path=f"/path/to/book{i}.pdf",
                title=f"Book {i}",
                author="Author",
                is_duplicate=False,
            )
            db.add(book)
        db.commit()

        token = create_access_token(viewer_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/v1/books/?page=2&limit=20", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["limit"] == 20
        assert data["total"] == 50
        assert data["pages"] == 3
        assert len(data["items"]) == 20

    def test_list_books_filter_title(self, client, viewer_user, db):
        """Test filtering by title."""
        books_data = [
            ("Python Programming", "Author A"),
            ("Java Basics", "Author B"),
            ("Python Advanced", "Author C"),
        ]

        for title, author in books_data:
            book = Book(
                filesystem_path=f"/path/to/{title}.pdf",
                title=title,
                author=author,
                is_duplicate=False,
            )
            db.add(book)
        db.commit()

        token = create_access_token(viewer_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(
            "/api/v1/books/?title=Python", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert all("Python" in item["title"] for item in data["items"])

    def test_list_books_filter_title_case_insensitive(self, client, viewer_user, db):
        """Test that title filtering is case-insensitive."""
        book = Book(
            filesystem_path="/path/to/book.pdf",
            title="Python Programming",
            author="Author",
            is_duplicate=False,
        )
        db.add(book)
        db.commit()

        token = create_access_token(viewer_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(
            "/api/v1/books/?title=python", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Python Programming"

    def test_list_books_filter_author(self, client, viewer_user, db):
        """Test filtering by author."""
        books_data = [
            ("Book A", "John Smith"),
            ("Book B", "Jane Doe"),
            ("Book C", "John Brown"),
        ]

        for title, author in books_data:
            book = Book(
                filesystem_path=f"/path/to/{title}.pdf",
                title=title,
                author=author,
                is_duplicate=False,
            )
            db.add(book)
        db.commit()

        token = create_access_token(viewer_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(
            "/api/v1/books/?author=John", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all("John" in item["author"] for item in data["items"])

    def test_list_books_filter_publisher(self, client, viewer_user, db):
        """Test filtering by publisher."""
        books_data = [
            ("Book A", "Author A", "Penguin"),
            ("Book B", "Author B", "Oxford"),
            ("Book C", "Author C", "Penguin Plus"),
        ]

        for title, author, publisher in books_data:
            book = Book(
                filesystem_path=f"/path/to/{title}.pdf",
                title=title,
                author=author,
                publisher=publisher,
                is_duplicate=False,
            )
            db.add(book)
        db.commit()

        token = create_access_token(viewer_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(
            "/api/v1/books/?publisher=Penguin", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all("Penguin" in item["publisher"] for item in data["items"])

    def test_list_books_exclude_duplicates(self, client, viewer_user, db):
        """Test that duplicate books are excluded from list."""
        book1 = Book(
            filesystem_path="/path/to/book1.pdf",
            title="Original",
            author="Author",
            is_duplicate=False,
        )
        book2 = Book(
            filesystem_path="/path/to/book2.pdf",
            title="Duplicate",
            author="Author",
            is_duplicate=True,
        )
        db.add(book1)
        db.add(book2)
        db.commit()

        token = create_access_token(viewer_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/v1/books/", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Original"

    def test_list_books_unauthenticated(self, client):
        """Test that unauthenticated request returns 401."""
        response = client.get("/api/v1/books/")

        assert response.status_code == 401
        assert "Missing authorization header" in response.json()["detail"]

    def test_list_books_invalid_token(self, client):
        """Test that invalid token returns 401."""
        headers = {"Authorization": "Bearer invalid_token"}

        response = client.get("/api/v1/books/", headers=headers)

        assert response.status_code == 401
        assert "Invalid or expired token" in response.json()["detail"]

    def test_list_books_max_limit_enforced(self, client, viewer_user, db):
        """Test that limit is capped at 100."""
        # Create 150 books
        for i in range(150):
            book = Book(
                filesystem_path=f"/path/to/book{i}.pdf",
                title=f"Book {i}",
                author="Author",
                is_duplicate=False,
            )
            db.add(book)
        db.commit()

        token = create_access_token(viewer_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        # Request with limit > 100
        response = client.get("/api/v1/books/?limit=200", headers=headers)

        # Should be rejected or capped at 100
        if response.status_code == 422:
            # Validation error (preferred)
            pass
        else:
            # Or capped at 100
            data = response.json()
            assert len(data["items"]) <= 100


class TestGetBookEndpoint:
    """Test the GET /books/{book_id} endpoint."""

    def test_get_book_success(self, client, viewer_user, sample_book):
        """Get a book successfully."""
        token = create_access_token(viewer_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(f"/api/v1/books/{sample_book.id}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_book.id
        assert data["title"] == "Sample Book"
        assert data["author"] == "John Doe"
        assert data["publisher"] == "Test Publisher"

    def test_get_book_not_found(self, client, viewer_user):
        """Get a non-existent book returns 404."""
        token = create_access_token(viewer_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/v1/books/999", headers=headers)

        assert response.status_code == 404
        assert "Book not found" in response.json()["detail"]

    def test_get_book_unauthenticated(self, client, sample_book):
        """Get book without authentication returns 401."""
        response = client.get(f"/api/v1/books/{sample_book.id}")

        assert response.status_code == 401


class TestUpdateBookEndpoint:
    """Test the PATCH /books/{book_id} endpoint."""

    def test_update_book_curator_success(self, client, curator_user, sample_book, db):
        """Curator can update book metadata."""
        token = create_access_token(curator_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.patch(
            f"/api/v1/books/{sample_book.id}",
            headers=headers,
            json={
                "title": "Updated Title",
                "author": "Updated Author",
                "publisher": "Updated Publisher",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["author"] == "Updated Author"
        assert data["publisher"] == "Updated Publisher"

        # Verify metadata_locked is set
        db_book = db.query(Book).filter(Book.id == sample_book.id).first()
        assert db_book.metadata_locked is True

    def test_update_book_admin_success(self, client, admin_user, sample_book, db):
        """Admin can update book metadata."""
        token = create_access_token(admin_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.patch(
            f"/api/v1/books/{sample_book.id}",
            headers=headers,
            json={"title": "Admin Updated Title"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Admin Updated Title"

        # Verify metadata_locked is set
        db_book = db.query(Book).filter(Book.id == sample_book.id).first()
        assert db_book.metadata_locked is True

    def test_update_book_viewer_forbidden(self, client, viewer_user, sample_book):
        """Viewer cannot update book metadata."""
        token = create_access_token(viewer_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.patch(
            f"/api/v1/books/{sample_book.id}",
            headers=headers,
            json={"title": "Viewer Attempt"},
        )

        assert response.status_code == 403
        assert "Insufficient permissions" in response.json()["detail"]

    def test_update_book_partial(self, client, curator_user, sample_book):
        """Update only some fields."""
        token = create_access_token(curator_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.patch(
            f"/api/v1/books/{sample_book.id}",
            headers=headers,
            json={"title": "New Title"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title"
        assert data["author"] == "John Doe"  # Unchanged
        assert data["publisher"] == "Test Publisher"  # Unchanged

    def test_update_book_not_found(self, client, curator_user):
        """Update non-existent book returns 404."""
        token = create_access_token(curator_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.patch(
            "/api/v1/books/999",
            headers=headers,
            json={"title": "New Title"},
        )

        assert response.status_code == 404
        assert "Book not found" in response.json()["detail"]

    def test_update_book_unauthenticated(self, client, sample_book):
        """Update without authentication returns 401."""
        response = client.patch(
            f"/api/v1/books/{sample_book.id}",
            json={"title": "New Title"},
        )

        assert response.status_code == 401


class TestDeleteBookEndpoint:
    """Test the DELETE /books/{book_id} endpoint."""

    def test_delete_book_admin_success(self, client, admin_user, sample_book, db):
        """Admin can delete a book."""
        token = create_access_token(admin_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.delete(
            f"/api/v1/books/{sample_book.id}", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"

        # Verify book is actually deleted
        db_book = db.query(Book).filter(Book.id == sample_book.id).first()
        assert db_book is None

    def test_delete_book_curator_forbidden(self, client, curator_user, sample_book):
        """Curator cannot delete a book."""
        token = create_access_token(curator_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.delete(
            f"/api/v1/books/{sample_book.id}", headers=headers
        )

        assert response.status_code == 403
        assert "Admin only" in response.json()["detail"]

    def test_delete_book_viewer_forbidden(self, client, viewer_user, sample_book):
        """Viewer cannot delete a book."""
        token = create_access_token(viewer_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.delete(
            f"/api/v1/books/{sample_book.id}", headers=headers
        )

        assert response.status_code == 403
        assert "Admin only" in response.json()["detail"]

    def test_delete_book_not_found(self, client, admin_user):
        """Delete non-existent book returns 404."""
        token = create_access_token(admin_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.delete("/api/v1/books/999", headers=headers)

        assert response.status_code == 404
        assert "Book not found" in response.json()["detail"]

    def test_delete_book_unauthenticated(self, client, sample_book):
        """Delete without authentication returns 401."""
        response = client.delete(f"/api/v1/books/{sample_book.id}")

        assert response.status_code == 401
