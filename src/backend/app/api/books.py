"""Book API endpoints for CRUD operations."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Book
from app.schemas import BookResponse
from app.services import BookService, BookQueryParams
from app.auth.jwt_handler import decode_token

router = APIRouter()


class BookUpdateRequest(BaseModel):
    """Request schema for updating a book."""

    title: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None


async def get_current_user(
    authorization: Optional[str] = Header(None), db: Session = Depends(get_db)
) -> User:
    """
    Dependency to extract current user from Bearer token.

    Args:
        authorization: Authorization header with Bearer token.
        db: Database session.

    Returns:
        User object if token is valid.

    Raises:
        HTTPException: 401 if token is missing or invalid.
        HTTPException: 404 if user not found in database.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    # Extract Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )

    token = parts[1]

    # Decode token
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    # Extract user_id from token payload
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Query user from database
    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
        )

    user = db.query(User).filter(User.id == user_id_int).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


@router.get("/")
async def list_books(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    title: Optional[str] = None,
    author: Optional[str] = None,
    publisher: Optional[str] = None,
):
    """
    List books with pagination and optional filtering.

    Query Parameters:
        - page: Page number (default: 1)
        - limit: Items per page (default: 20, max: 100)
        - title: Filter by title (case-insensitive, optional)
        - author: Filter by author (case-insensitive, optional)
        - publisher: Filter by publisher (case-insensitive, optional)

    Returns:
        Dictionary with items, total, page, limit, pages
    """
    params = BookQueryParams(
        page=page, limit=limit, title=title, author=author, publisher=publisher
    )

    result = BookService.list_books(db, params)

    # Transform items to BookResponse objects
    items = [BookResponse.model_validate(book) for book in result["items"]]

    return {
        "items": items,
        "total": result["total"],
        "page": result["page"],
        "limit": result["limit"],
        "pages": result["pages"],
    }


@router.get("/{book_id}")
async def get_book(
    book_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Get a single book by ID.

    Args:
        book_id: The ID of the book to retrieve.

    Returns:
        BookResponse with book details.
    """
    book = BookService.get_book(db, book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )

    return BookResponse.model_validate(book)


@router.patch("/{book_id}")
async def update_book(
    book_id: int,
    update_request: BookUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Update a book's metadata (curator+ only).

    Only users with 'admin' or 'curator' role can update book metadata.
    When updated, metadata_locked is set to True.

    Args:
        book_id: The ID of the book to update.
        update_request: BookUpdateRequest containing fields to update.

    Returns:
        Updated BookResponse.
    """
    # Check permissions
    if user.role not in ["admin", "curator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Only admin and curator can update books.",
        )

    # Update book with metadata_locked=True
    updated_book = BookService.update_book(
        db,
        book_id,
        title=update_request.title,
        author=update_request.author,
        publisher=update_request.publisher,
        metadata_locked=True,
    )

    if not updated_book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )

    return BookResponse.model_validate(updated_book)


@router.delete("/{book_id}")
async def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Delete a book (admin only).

    Args:
        book_id: The ID of the book to delete.

    Returns:
        Status message.
    """
    # Check permissions (admin only)
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin only. Only administrators can delete books.",
        )

    # Find and delete book
    book = BookService.get_book(db, book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )

    db.delete(book)
    db.commit()

    return {"status": "deleted"}
