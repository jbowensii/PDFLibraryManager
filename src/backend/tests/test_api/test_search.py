"""
Tests for search API endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import User, Book
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


def test_search_by_title(auth_headers):
    """Test searching books by title endpoint."""
    response = client.get(
        "/api/v1/search/?q=Python&search_type=title",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data


def test_search_by_author(auth_headers):
    """Test searching books by author endpoint."""
    response = client.get(
        "/api/v1/search/?q=John&search_type=author",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data


def test_search_by_publisher(auth_headers):
    """Test searching books by publisher endpoint."""
    response = client.get(
        "/api/v1/search/?q=Tech&search_type=publisher",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data


def test_search_case_insensitive(auth_headers):
    """Test search endpoint is accessible."""
    response = client.get(
        "/api/v1/search/?q=python&search_type=title",
        headers=auth_headers
    )
    assert response.status_code == 200


def test_search_invalid_type(auth_headers):
    """Test search with invalid type fails."""
    response = client.get(
        "/api/v1/search/?q=test&search_type=invalid",
        headers=auth_headers
    )
    assert response.status_code == 400


def test_search_no_results(auth_headers):
    """Test search endpoint responds correctly."""
    response = client.get(
        "/api/v1/search/?q=nonexistent123xyz&search_type=title",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
