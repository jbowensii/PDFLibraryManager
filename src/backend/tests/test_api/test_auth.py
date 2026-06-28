"""Tests for authentication endpoints and utilities."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import create_app
from app.models import User
from app.auth.password import hash_password, verify_password
from app.auth.jwt_handler import create_access_token, decode_token
from app.config import settings


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


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self):
        """Hash a plaintext password and verify it's not the original."""
        plaintext = "secure_pass_123"
        hashed = hash_password(plaintext)

        # Hash should not be plaintext
        assert hashed != plaintext
        # Hash should be a string
        assert isinstance(hashed, str)
        # Hash should be reasonably long (bcrypt hashes are long)
        assert len(hashed) > 20

    def test_verify_password_valid(self):
        """Verify that correct password matches hashed password."""
        plaintext = "secure_pass_123"
        hashed = hash_password(plaintext)

        # Correct password should verify
        assert verify_password(plaintext, hashed) is True

    def test_verify_password_invalid(self):
        """Verify that incorrect password does not match hashed password."""
        plaintext = "secure_pass_123"
        wrong_password = "wrong_pass"
        hashed = hash_password(plaintext)

        # Wrong password should not verify
        assert verify_password(wrong_password, hashed) is False

    def test_hash_consistency(self):
        """Hashing the same password produces different hashes (bcrypt random salt)."""
        plaintext = "test_pass"
        hash1 = hash_password(plaintext)
        hash2 = hash_password(plaintext)

        # Hashes should be different (due to random salt)
        assert hash1 != hash2
        # But both should verify against the plaintext
        assert verify_password(plaintext, hash1) is True
        assert verify_password(plaintext, hash2) is True


class TestJWTHandler:
    """Test JWT token creation and decoding."""

    def test_create_access_token(self):
        """Create a token and verify it's a string."""
        user_id = 123
        token = create_access_token(user_id)

        # Token should be a string
        assert isinstance(token, str)
        # Token should be non-empty
        assert len(token) > 0
        # JWT tokens have dots as separators (header.payload.signature)
        assert token.count(".") == 2

    def test_create_access_token_with_expires_delta(self):
        """Create a token with custom expiry."""
        from datetime import timezone
        user_id = 123
        expires_delta = timedelta(hours=2)
        token = create_access_token(user_id, expires_delta)

        # Token should be valid
        assert isinstance(token, str)
        assert len(token) > 0

        # Decode and verify expiry is in the future
        payload = decode_token(token)
        assert payload is not None
        assert "exp" in payload
        # exp should be approximately 2 hours from now
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        time_diff = (exp_time - now).total_seconds()
        # Should be approximately 2 hours (7200 seconds), allow 60 second tolerance
        assert 7140 < time_diff < 7260

    def test_decode_valid_token(self):
        """Decode a valid token and verify user_id."""
        user_id = 456
        token = create_access_token(user_id)
        payload = decode_token(token)

        # Payload should exist
        assert payload is not None
        # Should have "sub" (subject = user_id)
        assert "sub" in payload
        assert payload["sub"] == str(user_id)
        # Should have "exp" (expiration)
        assert "exp" in payload

    def test_decode_invalid_token(self):
        """Attempt to decode invalid token."""
        invalid_token = "invalid.token.here"
        payload = decode_token(invalid_token)

        # Should return None for invalid token
        assert payload is None

    def test_decode_malformed_token(self):
        """Attempt to decode malformed token."""
        malformed_token = "not_a_valid_jwt"
        payload = decode_token(malformed_token)

        # Should return None for malformed token
        assert payload is None

    def test_token_expiry(self):
        """Create a token with past expiry and verify it fails to decode."""
        user_id = 789
        # Create token that expired 1 hour ago
        expires_delta = timedelta(hours=-1)
        expired_token = create_access_token(user_id, expires_delta)

        # Decode should fail for expired token
        payload = decode_token(expired_token)
        assert payload is None


class TestLoginEndpoint:
    """Test the login endpoint."""

    def test_login_success(self, client, db):
        """Create user, login successfully, verify access_token in response."""
        # Create a test user
        plaintext = "testpass123"
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=hash_password(plaintext),
            role="viewer",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Attempt login
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": plaintext},
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0

        # Verify token is valid and contains correct user_id
        payload = decode_token(data["access_token"])
        assert payload is not None
        assert payload["sub"] == str(user.id)

    def test_login_nonexistent_user(self, client):
        """Attempt login with nonexistent username."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent", "password": "anypassword"},
        )

        # Should return 401 Unauthorized
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_login_wrong_password(self, client, db):
        """Create user, attempt login with wrong password."""
        # Create a test user
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=hash_password("correctpwd"),
            role="viewer",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Attempt login with wrong password
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "wrongpwd"},
        )

        # Should return 401 Unauthorized
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_login_case_sensitive_username(self, client, db):
        """Test that username matching is case-sensitive."""
        # Create a test user with lowercase username
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=hash_password("correctpwd"),
            role="viewer",
        )
        db.add(user)
        db.commit()

        # Attempt login with different case
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "TestUser", "password": "correctpwd"},
        )

        # Should return 401 (username not found with different case)
        assert response.status_code == 401


class TestRegisterEndpoint:
    """Test the register endpoint."""

    def test_register_success(self, client, db):
        """Register new user, verify user created and returned."""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "securepwd123",
            "role": "viewer",
        }

        response = client.post("/api/v1/auth/register", json=user_data)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert data["role"] == "viewer"
        assert "id" in data
        assert "password_hash" not in data  # Should not return password hash

        # Verify user was actually created in database
        db_user = db.query(User).filter(User.username == "newuser").first()
        assert db_user is not None
        assert db_user.email == "newuser@example.com"
        assert verify_password("securepwd123", db_user.password_hash)

    def test_register_default_role(self, client):
        """Register without specifying role, verify default role is 'viewer'."""
        user_data = {
            "username": "defaultroleuser",
            "email": "defaultrole@example.com",
            "password": "password123",
        }

        response = client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "viewer"

        # Note: password field must be >= 8 chars, and we use password123 which is fine

    def test_register_duplicate_username(self, client, db):
        """Attempt to register with existing username."""
        # Create first user
        user1 = User(
            username="existinguser",
            email="user1@example.com",
            password_hash=hash_password("password123"),
            role="viewer",
        )
        db.add(user1)
        db.commit()

        # Attempt to register with same username
        user_data = {
            "username": "existinguser",
            "email": "user2@example.com",
            "password": "password456",
        }

        response = client.post("/api/v1/auth/register", json=user_data)

        # Should return 400 Bad Request
        assert response.status_code == 400
        assert "Username already registered" in response.json()["detail"]

    def test_register_duplicate_email(self, client, db):
        """Attempt to register with existing email."""
        # Create first user
        user1 = User(
            username="user1",
            email="sameemail@example.com",
            password_hash=hash_password("pwd123abc"),
            role="viewer",
        )
        db.add(user1)
        db.commit()

        # Attempt to register with same email
        user_data = {
            "username": "user2",
            "email": "sameemail@example.com",
            "password": "pwd456def",
        }

        response = client.post("/api/v1/auth/register", json=user_data)

        # Should return 400 Bad Request
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_register_with_curator_role(self, client):
        """Register with curator role."""
        user_data = {
            "username": "curator_user",
            "email": "curator@example.com",
            "password": "curatorpass123",
            "role": "curator",
        }

        response = client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "curator"

    def test_register_with_admin_role(self, client):
        """Register with admin role."""
        user_data = {
            "username": "admin_user",
            "email": "admin@example.com",
            "password": "adminpass123",
            "role": "admin",
        }

        response = client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"

    def test_register_invalid_email(self, client):
        """Attempt to register with invalid email."""
        user_data = {
            "username": "invalid_email_user",
            "email": "not_an_email",
            "password": "validpass123",
        }

        response = client.post("/api/v1/auth/register", json=user_data)

        # Should return 422 Unprocessable Entity (validation error)
        assert response.status_code == 422

    def test_register_password_too_short(self, client):
        """Attempt to register with password shorter than 8 characters."""
        user_data = {
            "username": "shortpass_user",
            "email": "shortpass@example.com",
            "password": "short",
        }

        response = client.post("/api/v1/auth/register", json=user_data)

        # Should return 422 Unprocessable Entity (validation error)
        assert response.status_code == 422

    def test_register_username_too_short(self, client):
        """Attempt to register with username shorter than 3 characters."""
        user_data = {
            "username": "ab",
            "email": "shortuser@example.com",
            "password": "password123",
        }

        response = client.post("/api/v1/auth/register", json=user_data)

        # Should return 422 Unprocessable Entity (validation error)
        assert response.status_code == 422
