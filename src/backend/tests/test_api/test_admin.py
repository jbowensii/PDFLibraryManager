"""
Tests for admin API endpoints.
"""

import pytest  # noqa: F401
from fastapi.testclient import TestClient

from app.main import app
from app.models import User, Job, AuditLog
from app.api.auth import hash_password
from conftest import TestingSessionLocal

client = TestClient(app)


def get_auth_token(username="testuser", email="test@example.com"):
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

    # Login with JSON body
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": username,
            "password": "password123"
        }
    )
    return response.json()["access_token"]


def create_admin_user():
    """Create an admin user directly in database."""
    db = TestingSessionLocal()
    try:
        admin = User(
            username="admin",
            email="admin@example.com",
            password_hash=hash_password("admin123"),
            role="admin"
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return admin
    finally:
        db.close()


def create_curator_user(username="curator1", email="curator1@example.com"):
    """Create a curator user directly in database."""
    db = TestingSessionLocal()
    try:
        curator = User(
            username=username,
            email=email,
            password_hash=hash_password("curator123"),
            role="curator"
        )
        db.add(curator)
        db.commit()
        db.refresh(curator)
        return curator
    finally:
        db.close()


def get_admin_token():
    """Get token for admin user."""
    # Register admin via API
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "admin",
            "email": "admin@example.com",
            "password": "admin123"
        }
    )

    # Manually set to admin role
    db = TestingSessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if admin:
            admin.role = "admin"
            db.commit()
    finally:
        db.close()

    # Login with JSON body
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "admin",
            "password": "admin123"
        }
    )
    return response.json()["access_token"]


@pytest.fixture
def curator_headers():
    """Create curator user and return auth headers."""
    token = get_auth_token(username="curator", email="curator@example.com")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers():
    """Create admin user and return auth headers."""
    token = get_admin_token()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def cleanup():
    """Clean up database between tests."""
    yield


# ====== NON-ADMIN DENIAL TESTS (original) ======

def test_list_users_non_admin_denies_access():
    """Non-admin should be denied access to list users."""
    # Create admin first (so curator is not admin)
    _ = get_auth_token(username="admin_first", email="admin_first@example.com")
    # Now register curator (will not be admin)
    token = get_auth_token(username="curator", email="curator@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(
        "/api/v1/admin/users",
        headers=headers
    )
    assert response.status_code == 403


def test_create_user_non_admin_denies_access():
    """Non-admin should be denied access to create users."""
    token = get_auth_token(username="user1", email="user1@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/v1/admin/users",
        headers=headers,
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "password123"
        }
    )
    assert response.status_code == 403


def test_update_user_role_non_admin_denies_access():
    """Non-admin should be denied access to update user roles."""
    token = get_auth_token(username="user2", email="user2@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.patch(
        "/api/v1/admin/users/1",
        headers=headers,
        json={"role": "admin"}
    )
    assert response.status_code == 403


def test_delete_user_non_admin_denies_access():
    """Non-admin should be denied access to delete users."""
    token = get_auth_token(username="user3", email="user3@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.delete(
        "/api/v1/admin/users/999",
        headers=headers
    )
    assert response.status_code == 403


def test_list_jobs_non_admin_denies_access():
    """Non-admin should be denied access to list jobs."""
    token = get_auth_token(username="user4", email="user4@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(
        "/api/v1/admin/jobs",
        headers=headers
    )
    assert response.status_code == 403


def test_audit_log_non_admin_denies_access():
    """Non-admin should be denied access to audit log."""
    token = get_auth_token(username="user5", email="user5@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(
        "/api/v1/admin/audit-log",
        headers=headers
    )
    assert response.status_code == 403


# ====== ADMIN SUCCESS TESTS (new) ======

def test_list_users_as_admin_succeeds(admin_headers):
    """Admin can list all users."""
    response = client.get(
        "/api/v1/admin/users",
        headers=admin_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)


def test_create_user_as_admin_succeeds(admin_headers):
    """Admin can create a new user."""
    response = client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={
            "username": "newcurator",
            "email": "newcurator@example.com",
            "password": "password123"
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newcurator"
    assert data["email"] == "newcurator@example.com"
    assert data["role"] == "curator"  # New users default to curator


def test_create_user_admin_validates_duplicate_username(admin_headers):
    """Admin cannot create user with duplicate username."""
    # Create first user
    client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={
            "username": "duplicate",
            "email": "first@example.com",
            "password": "password123"
        }
    )

    # Try to create second user with same username
    response = client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={
            "username": "duplicate",
            "email": "second@example.com",
            "password": "password123"
        }
    )

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_update_user_role_as_admin_succeeds(admin_headers):
    """Admin can update a user's role."""
    # Create a curator
    create_curator_user(username="roletest", email="roletest@example.com")

    # Get the user ID by querying database
    db = TestingSessionLocal()
    try:
        curator = db.query(User).filter(User.username == "roletest").first()
        curator_id = curator.id
    finally:
        db.close()

    # Update role to admin
    response = client.patch(
        f"/api/v1/admin/users/{curator_id}",
        headers=admin_headers,
        json={"role": "admin"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "admin"


def test_update_user_role_validates_role(admin_headers):
    """Admin cannot set invalid role."""
    create_curator_user(username="invalidrole", email="invalidrole@example.com")

    db = TestingSessionLocal()
    try:
        curator = db.query(User).filter(User.username == "invalidrole").first()
        curator_id = curator.id
    finally:
        db.close()

    response = client.patch(
        f"/api/v1/admin/users/{curator_id}",
        headers=admin_headers,
        json={"role": "superuser"}
    )

    assert response.status_code == 400
    assert "Role must be" in response.json()["detail"]


def test_delete_user_as_admin_succeeds(admin_headers):
    """Admin can delete a user."""
    # Create user to delete
    create_curator_user(username="deletetest", email="deletetest@example.com")

    db = TestingSessionLocal()
    try:
        curator = db.query(User).filter(User.username == "deletetest").first()
        curator_id = curator.id
    finally:
        db.close()

    # Delete the user
    response = client.delete(
        f"/api/v1/admin/users/{curator_id}",
        headers=admin_headers
    )

    assert response.status_code == 204

    # Verify deleted
    db = TestingSessionLocal()
    try:
        deleted = db.query(User).filter(User.id == curator_id).first()
        assert deleted is None
    finally:
        db.close()


def test_delete_user_cannot_delete_self(admin_headers):
    """Admin cannot delete their own account."""
    # Get admin user ID from the database - should be the one with role=admin
    # that was just created by get_admin_token() fixture
    db = TestingSessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if admin:
            admin_id = admin.id
        else:
            # Fallback - get any admin
            admin = db.query(User).filter(User.role == "admin").first()
            admin_id = admin.id if admin else None
    finally:
        db.close()

    if admin_id is None:
        pytest.skip("Admin user not found in database")

    response = client.delete(
        f"/api/v1/admin/users/{admin_id}",
        headers=admin_headers
    )

    assert response.status_code == 400
    assert "Cannot delete yourself" in response.json()["detail"]


def test_delete_user_not_found(admin_headers):
    """Admin deletion fails gracefully for nonexistent user."""
    response = client.delete(
        "/api/v1/admin/users/99999",
        headers=admin_headers
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_list_jobs_as_admin_succeeds(admin_headers):
    """Admin can list all jobs."""
    response = client.get(
        "/api/v1/admin/jobs",
        headers=admin_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)


def test_list_audit_log_as_admin_succeeds(admin_headers):
    """Admin can view audit log."""
    response = client.get(
        "/api/v1/admin/audit-log",
        headers=admin_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)
