"""Business logic for book operations."""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.models import Book


class BookQueryParams(BaseModel):
    """Query parameters for listing books."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    limit: int = Field(
        default=20, ge=1, le=100, description="Items per page (max 100)"
    )
    title: Optional[str] = Field(None, description="Filter by title (case-insensitive)")
    author: Optional[str] = Field(
        None, description="Filter by author (case-insensitive)"
    )
    publisher: Optional[str] = Field(
        None, description="Filter by publisher (case-insensitive)"
    )


class BookService:
    """Service for book business logic operations."""

    @staticmethod
    def list_books(db: Session, params: BookQueryParams) -> Dict[str, Any]:
        """
        List books with pagination and optional filtering.

        Filters by is_duplicate=False to only show non-duplicates.

        Args:
            db: Database session.
            params: BookQueryParams containing page, limit, and optional filters.

        Returns:
            Dictionary with keys: items, total, page, limit, pages
        """
        # Start with base query: filter out duplicates
        query = db.query(Book).filter(Book.is_duplicate == False)

        # Apply optional filters (case-insensitive)
        if params.title:
            query = query.filter(
                Book.title.ilike(f"%{params.title}%")
            )
        if params.author:
            query = query.filter(
                Book.author.ilike(f"%{params.author}%")
            )
        if params.publisher:
            query = query.filter(
                Book.publisher.ilike(f"%{params.publisher}%")
            )

        # Get total count before pagination
        total = query.count()

        # Calculate pagination
        offset = (params.page - 1) * params.limit
        total_pages = (total + params.limit - 1) // params.limit

        # Apply pagination
        books = query.offset(offset).limit(params.limit).all()

        return {
            "items": books,
            "total": total,
            "page": params.page,
            "limit": params.limit,
            "pages": total_pages,
        }

    @staticmethod
    def get_book(db: Session, book_id: int) -> Optional[Book]:
        """
        Get a single book by ID.

        Args:
            db: Database session.
            book_id: The ID of the book to retrieve.

        Returns:
            Book object or None if not found.
        """
        return db.query(Book).filter(Book.id == book_id).first()

    @staticmethod
    def update_book(db: Session, book_id: int, **kwargs) -> Optional[Book]:
        """
        Update a book's metadata fields.

        Args:
            db: Database session.
            book_id: The ID of the book to update.
            **kwargs: Keyword arguments of fields to update (title, author, publisher).
                     Only non-None values are applied.

        Returns:
            Updated Book object or None if not found.
        """
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            return None

        # Update only non-None attributes that exist on the Book model
        for key, value in kwargs.items():
            if value is not None and hasattr(book, key):
                setattr(book, key, value)

        # Commit changes and refresh
        db.commit()
        db.refresh(book)

        return book
