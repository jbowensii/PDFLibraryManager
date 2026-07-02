"""
Books API endpoints - list, get details, and delete books.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..models import Book, User
from ..schemas import BookResponse, BookDetailResponse
from ..database import get_db
from .auth import get_current_user

router = APIRouter()


@router.get('/', response_model=dict)
async def list_books(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """
    List books with pagination.

    Args:
        skip: Number of books to skip
        limit: Number of books to return
        db: Database session
        user: Current authenticated user

    Returns:
        dict: Total count and list of books
    """
    # Get total count
    total = db.query(Book).count()

    # Get paginated results
    books = db.query(Book).offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [BookResponse.from_orm(book) for book in books]
    }


@router.get('/{book_id}', response_model=BookDetailResponse)
async def get_book(
    book_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BookDetailResponse:
    """
    Get detailed information about a specific book.

    Args:
        book_id: ID of the book
        db: Database session
        user: Current authenticated user

    Returns:
        BookDetailResponse: Detailed book information

    Raises:
        HTTPException: If book not found
    """
    book = db.query(Book).filter(Book.id == book_id).first()

    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book {book_id} not found"
        )

    return BookDetailResponse.from_orm(book)


@router.delete('/{book_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """
    Delete a book. Only admins can delete books.

    Args:
        book_id: ID of the book to delete
        db: Database session
        user: Current authenticated user

    Raises:
        HTTPException: If user is not admin or book not found
    """
    if user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete books"
        )

    book = db.query(Book).filter(Book.id == book_id).first()

    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book {book_id} not found"
        )

    db.delete(book)
    db.commit()
