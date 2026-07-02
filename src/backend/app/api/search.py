"""
Search API endpoints - search books by title, author, or publisher.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..models import Book, User
from ..schemas import SearchResponse, BookSearchResponse
from ..database import get_db
from .auth import get_current_user

router = APIRouter()


@router.get('/', response_model=SearchResponse)
async def search_books(
    q: str,
    search_type: str = 'title',
    limit: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SearchResponse:
    """
    Search for books by title, author, or publisher.

    Args:
        q: Search query string
        search_type: Type of search - 'title', 'author', or 'publisher'
        limit: Maximum number of results to return
        db: Database session
        user: Current authenticated user

    Returns:
        SearchResponse: Total count and matching books

    Raises:
        HTTPException: If search_type is invalid
    """
    if search_type not in ['title', 'author', 'publisher']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="search_type must be 'title', 'author', or 'publisher'"
        )

    # Build query based on search type
    query = db.query(Book)

    if search_type == 'title':
        query = query.filter(Book.title.ilike(f'%{q}%'))
    elif search_type == 'author':
        query = query.filter(Book.author.ilike(f'%{q}%'))
    elif search_type == 'publisher':
        query = query.filter(Book.publisher.ilike(f'%{q}%'))

    # Execute query
    books = query.limit(limit).all()
    total = query.count()

    return SearchResponse(
        total=total,
        items=[BookSearchResponse.from_orm(book) for book in books]
    )
