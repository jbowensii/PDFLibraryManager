"""
Audit logging utility for tracking all system mutations.

Provides centralized audit event recording across all endpoints.
"""

import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.models import AuditLog

logger = logging.getLogger(__name__)


def log_audit(
    db: Session,
    user_id: Optional[int],
    action: str,
    details: Optional[str] = None,
) -> Optional[AuditLog]:
    """
    Log an audit event to the database.

    Args:
        db: Database session
        user_id: ID of the user performing the action (None for system actions)
        action: Type of action (e.g., "create_user", "update_book", "delete_collection")
        details: Optional additional details about the action

    Returns:
        AuditLog: The created audit log entry, or None if logging failed

    Example:
        log_audit(db, user.id, "create_book", details=f"book_id={book.id}, title={book.title}")
    """
    try:
        audit_entry = AuditLog(
            user_id=user_id,
            action=action,
            details=details,
            created_at=datetime.utcnow()
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(audit_entry)
        logger.debug(f"Audit logged: user_id={user_id}, action={action}")
        return audit_entry
    except Exception as e:
        logger.error(f"Failed to log audit event: action={action}, error={e}")
        # Don't raise; audit failures should not break the application
        return None


def log_user_action(
    db: Session,
    user_id: int,
    action: str,
    details: Optional[str] = None,
) -> Optional[AuditLog]:
    """
    Log a user action.

    Args:
        db: Database session
        user_id: ID of the user performing the action
        action: Type of action (e.g., "register_user", "update_user_role")
        details: Optional details

    Returns:
        AuditLog: Created audit entry or None if failed
    """
    return log_audit(db, user_id, action, details)


def log_book_action(
    db: Session,
    user_id: int,
    action: str,
    book_id: int,
    details: Optional[str] = None,
) -> Optional[AuditLog]:
    """
    Log a book-related action.

    Args:
        db: Database session
        user_id: ID of the user performing the action
        action: Type of action (e.g., "update_book", "delete_book")
        book_id: ID of the book
        details: Optional details

    Returns:
        AuditLog: Created audit entry or None if failed
    """
    detail_str = f"book_id={book_id}"
    if details:
        detail_str += f", {details}"
    return log_audit(db, user_id, action, detail_str)


def log_collection_action(
    db: Session,
    user_id: int,
    action: str,
    collection_id: int,
    details: Optional[str] = None,
) -> Optional[AuditLog]:
    """
    Log a collection-related action.

    Args:
        db: Database session
        user_id: ID of the user performing the action
        action: Type of action (e.g., "create_collection", "delete_collection")
        collection_id: ID of the collection
        details: Optional details

    Returns:
        AuditLog: Created audit entry or None if failed
    """
    detail_str = f"collection_id={collection_id}"
    if details:
        detail_str += f", {details}"
    return log_audit(db, user_id, action, detail_str)


def log_duplicate_action(
    db: Session,
    user_id: int,
    action: str,
    duplicate_candidate_id: int,
    details: Optional[str] = None,
) -> Optional[AuditLog]:
    """
    Log a duplicate handling action.

    Args:
        db: Database session
        user_id: ID of the user performing the action
        action: Type of action (e.g., "resolve_duplicate", "flag_duplicate")
        duplicate_candidate_id: ID of the duplicate candidate
        details: Optional details

    Returns:
        AuditLog: Created audit entry or None if failed
    """
    detail_str = f"duplicate_id={duplicate_candidate_id}"
    if details:
        detail_str += f", {details}"
    return log_audit(db, user_id, action, detail_str)
