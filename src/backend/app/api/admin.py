"""
Admin API endpoints - manage users, view jobs and audit logs.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..models import User, Job, AuditLog
from ..schemas import UserListResponse, AuditLogResponse, UserCreate, UserUpdate, JobResponse
from ..database import get_db
from .auth import hash_password, get_current_user

router = APIRouter()


def _check_admin(user: User) -> None:
    """Check if user is admin."""
    if user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )


@router.get('/users', response_model=dict)
async def list_users(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """
    List all users. Only admins can access.

    Args:
        skip: Number of users to skip
        limit: Number of users to return
        db: Database session
        user: Current authenticated user

    Returns:
        dict: Total count and list of users

    Raises:
        HTTPException: If user is not admin
    """
    _check_admin(user)

    total = db.query(User).count()
    users = db.query(User).offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [UserListResponse.from_orm(u) for u in users]
    }


@router.post('/users', response_model=UserListResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserListResponse:
    """
    Create a new user. Only admins can access.

    Args:
        user_data: User creation data
        db: Database session
        current_user: Current authenticated user

    Returns:
        UserListResponse: The created user

    Raises:
        HTTPException: If user is not admin, username/email exists
    """
    _check_admin(current_user)

    # Check if username exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # Check if email exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )

    # Create new user
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role='curator'
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserListResponse.from_orm(new_user)


@router.patch('/users/{user_id}', response_model=UserListResponse)
async def update_user_role(
    user_id: int,
    request: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserListResponse:
    """
    Update a user's role. Only admins can access.

    Args:
        user_id: ID of the user to update
        request: Update data with new role
        db: Database session
        current_user: Current authenticated user

    Returns:
        UserListResponse: The updated user

    Raises:
        HTTPException: If user is not admin, target user not found, or invalid role
    """
    _check_admin(current_user)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )

    if request.role:
        if request.role not in ['admin', 'curator', 'viewer']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role must be 'admin', 'curator', or 'viewer'"
            )
        user.role = request.role

    db.commit()
    db.refresh(user)

    return UserListResponse.from_orm(user)


@router.delete('/users/{user_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Delete a user. Only admins can access.

    Args:
        user_id: ID of the user to delete
        db: Database session
        current_user: Current authenticated user

    Raises:
        HTTPException: If user is not admin, target user not found, or trying to delete self
    """
    _check_admin(current_user)

    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )

    db.delete(user)
    db.commit()


@router.get('/jobs', response_model=dict)
async def list_jobs(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """
    List all jobs. Only admins can access.

    Args:
        skip: Number of jobs to skip
        limit: Number of jobs to return
        db: Database session
        user: Current authenticated user

    Returns:
        dict: Total count and list of jobs

    Raises:
        HTTPException: If user is not admin
    """
    _check_admin(user)

    total = db.query(Job).count()
    jobs = db.query(Job).offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [JobResponse.from_orm(j) for j in jobs]
    }


@router.get('/audit-log', response_model=dict)
async def get_audit_log(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """
    Get audit log entries. Only admins can access.

    Args:
        skip: Number of entries to skip
        limit: Number of entries to return
        db: Database session
        user: Current authenticated user

    Returns:
        dict: Total count and list of audit log entries

    Raises:
        HTTPException: If user is not admin
    """
    _check_admin(user)

    total = db.query(AuditLog).count()
    entries = db.query(AuditLog).order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [AuditLogResponse.from_orm(e) for e in entries]
    }
