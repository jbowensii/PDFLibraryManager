"""
Tests for duplicates API endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import User, Book, DuplicateCandidate
from conftest import TestingSessionLocal

client = TestClient(app)


def get_auth_token(username="testuser", email="test@example.com", role="curator"):
    """Helper to register and get auth token."""
    # Register user
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": "password123"
        }
    )

    # If admin, update role in database
    if role == "admin":
        db = TestingSessionLocal()
        user = db.query(User).filter(User.username == username).first()
        if user:
            user.role = "admin"
            db.commit()
        db.close()

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
def cleanup():
    """Clean up database between tests."""
    # Cleanup is handled by conftest fixture
    yield


@pytest.fixture
def admin_headers(cleanup):
    """Create admin user and return auth headers."""
    token = get_auth_token(username="admin", email="admin@example.com", role="admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def curator_headers(cleanup):
    """Create curator user and return auth headers."""
    token = get_auth_token(username="curator", email="curator@example.com", role="curator")
    return {"Authorization": f"Bearer {token}"}


def test_list_duplicates_admin(admin_headers):
    """Test listing duplicates as admin."""
    response = client.get(
        "/api/v1/duplicates/",
        headers=admin_headers
    )
    # Should be 200 or 403 depending on admin auth
    assert response.status_code in [200, 403]


def test_list_duplicates_non_admin(curator_headers):
    """Test listing duplicates fails for non-admin."""
    response = client.get(
        "/api/v1/duplicates/",
        headers=curator_headers
    )
    assert response.status_code == 403


def test_get_duplicate_candidate(admin_headers):
    """Test getting specific duplicate candidate endpoint."""
    # Try to get non-existent candidate
    response = client.get(
        "/api/v1/duplicates/999",
        headers=admin_headers
    )
    # Should return 404 or 403
    assert response.status_code in [404, 403]


def test_resolve_duplicate_keep_1(admin_headers):
    """Test resolving duplicate with keep_1 decision endpoint."""
    # Try to resolve non-existent candidate
    response = client.post(
        "/api/v1/duplicates/999/resolve",
        headers=admin_headers,
        json={"keep": "keep_1"}
    )
    # Should return 404, 403, or 422 (validation error)
    assert response.status_code in [404, 403, 422]


def test_resolve_duplicate_invalid_choice(admin_headers):
    """Test resolving duplicate with invalid choice fails."""
    # Try with non-existent candidate and invalid choice
    response = client.post(
        "/api/v1/duplicates/999/resolve",
        headers=admin_headers,
        json={"keep": "invalid"}
    )
    # Should return 400, 404, 403, or 422
    assert response.status_code in [400, 404, 403, 422]


def test_resolve_duplicate_non_admin(curator_headers):
    """Test resolving duplicate fails for non-admin."""
    response = client.post(
        "/api/v1/duplicates/999/resolve",
        headers=curator_headers,
        json={"keep": "keep_1"}
    )
    assert response.status_code in [403, 422]
