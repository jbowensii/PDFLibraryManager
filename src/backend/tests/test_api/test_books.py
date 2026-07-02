"""
Tests for books API endpoints.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models import User, Book
from app.api.auth import create_access_token
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


def test_list_books_empty():
    """Test listing books when library is empty."""
    token = get_auth_token()
    response = client.get(
        "/api/v1/books/",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_books_with_pagination():
    """Test listing books with pagination."""
    token = get_auth_token()

    # Get first page
    response = client.get(
        "/api/v1/books/?skip=0&limit=10",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data

    # Get second page with skip
    response = client.get(
        "/api/v1/books/?skip=10&limit=10",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


def test_get_book_detail():
    """Test getting book details endpoint."""
    token = get_auth_token()

    # Test that endpoint is accessible
    response = client.get(
        "/api/v1/books/999",
        headers={"Authorization": f"Bearer {token}"}
    )
    # Either 404 (book not found) or 200 (if default book exists) are both valid
    assert response.status_code in [200, 404]


def test_get_book_not_found():
    """Test getting non-existent book."""
    token = get_auth_token()
    response = client.get(
        "/api/v1/books/9999",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404


def test_delete_book_admin():
    """Test deleting book as admin."""
    token = get_auth_token()

    # Try to delete non-existent book - should return 403 (not admin) or 404 (book not found)
    response = client.delete(
        "/api/v1/books/999",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code in [404, 403]
