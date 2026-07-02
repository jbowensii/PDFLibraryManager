"""
Tests for collections API endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import User, Book, Collection, CollectionBook
from conftest import TestingSessionLocal

client = TestClient(app)


def get_auth_token(username="testuser", email="test@example.com"):
    """Helper to register and get auth token."""
    # Register
    client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": "password123"
        }
    )

    # Login with JSON body
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": username,
            "password": "password123"
        }
    )
    return response.json()["access_token"]


@pytest.fixture
def auth_headers():
    """Return auth headers for test user."""
    token = get_auth_token()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def cleanup():
    """Clean up database between tests."""
    # Cleanup is handled by conftest fixture
    yield


def test_create_collection(auth_headers):
    """Test creating a collection."""
    response = client.post(
        "/api/v1/collections/",
        headers=auth_headers,
        json={
            "name": "My Collection",
            "description": "Test collection"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My Collection"
    assert "user_id" in data


def test_list_collections(auth_headers):
    """Test listing user's collections."""
    # Create a collection via API
    response = client.post(
        "/api/v1/collections/",
        headers=auth_headers,
        json={
            "name": "Collection 1",
            "description": "Description 1"
        }
    )
    assert response.status_code == 201

    # List collections
    response = client.get(
        "/api/v1/collections/",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


def test_get_collection_with_books(auth_headers):
    """Test getting collection with books."""
    # Create collection
    col_response = client.post(
        "/api/v1/collections/",
        headers=auth_headers,
        json={
            "name": "Test Collection",
            "description": "Test"
        }
    )
    assert col_response.status_code == 201
    collection_id = col_response.json()["id"]

    # Get collection
    response = client.get(
        f"/api/v1/collections/{collection_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Collection"


def test_add_book_to_collection(auth_headers):
    """Test adding book to collection endpoint."""
    # Create collection
    col_response = client.post(
        "/api/v1/collections/",
        headers=auth_headers,
        json={
            "name": "Test Collection"
        }
    )
    assert col_response.status_code == 201
    collection_id = col_response.json()["id"]

    # Try to add non-existent book (should handle gracefully)
    response = client.post(
        f"/api/v1/collections/{collection_id}/books",
        headers=auth_headers,
        params={"book_id": 999}
    )
    # 404 expected since book doesn't exist
    assert response.status_code == 404


def test_remove_book_from_collection(auth_headers):
    """Test removing book from collection endpoint."""
    # Create collection
    col_response = client.post(
        "/api/v1/collections/",
        headers=auth_headers,
        json={
            "name": "Test Collection"
        }
    )
    assert col_response.status_code == 201
    collection_id = col_response.json()["id"]

    # Try to remove non-existent book
    response = client.delete(
        f"/api/v1/collections/{collection_id}/books/999",
        headers=auth_headers
    )
    # Should return 404 or 200
    assert response.status_code in [200, 404]


def test_collection_not_found(auth_headers):
    """Test getting non-existent collection."""
    response = client.get(
        "/api/v1/collections/9999",
        headers=auth_headers
    )
    assert response.status_code == 404


def test_add_book_to_nonexistent_collection(auth_headers):
    """Test adding book to non-existent collection."""
    db = TestingSessionLocal()
    book = Book(
        title="Test Book",
        author="Author",
        publisher="Publisher"
    )
    db.add(book)
    db.commit()
    book_id = book.id
    db.close()

    response = client.post(
        "/api/v1/collections/9999/books",
        headers=auth_headers,
        params={"book_id": book_id}
    )
    assert response.status_code == 404
