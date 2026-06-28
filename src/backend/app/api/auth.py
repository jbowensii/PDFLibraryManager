"""Authentication API endpoints."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserResponse
from app.auth.password import hash_password, verify_password
from app.auth.jwt_handler import create_access_token

router = APIRouter()


class LoginRequest(BaseModel):
    """Request schema for user login."""

    username: str
    password: str


class LoginResponse(BaseModel):
    """Response schema for user login."""

    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login endpoint. Authenticates user and returns JWT access token.

    Args:
        request: LoginRequest containing username and password.
        db: Database session dependency.

    Returns:
        LoginResponse with access token and token type.

    Raises:
        HTTPException: 401 if credentials are invalid.
    """
    # Query user by username
    user = db.query(User).filter(User.username == request.username).first()

    # Check if user exists and password is correct
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Create access token with 30-minute expiry
    access_token = create_access_token(
        user.id, expires_delta=timedelta(minutes=30)
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register endpoint. Creates a new user account.

    Args:
        user_data: UserCreate schema containing username, email, password, and role.
        db: Database session dependency.

    Returns:
        UserResponse with created user details.

    Raises:
        HTTPException: 400 if username or email already exist.
    """
    # Check if username already exists
    existing_user_by_username = (
        db.query(User).filter(User.username == user_data.username).first()
    )
    if existing_user_by_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Check if email already exists
    existing_user_by_email = (
        db.query(User).filter(User.email == user_data.email).first()
    )
    if existing_user_by_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user with hashed password
    hashed_password = hash_password(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password,
        role=user_data.role,
    )

    # Add user to database
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user
