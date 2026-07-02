"""
Collections API endpoints - create, list, and manage user collections.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..models import Collection, CollectionBook, Book, User
from ..schemas import CollectionCreate, CollectionResponse, CollectionDetailResponse, BookSearchResponse
from ..database import get_db
from .auth import get_current_user

router = APIRouter()


@router.post('/', response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(
    request: CollectionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CollectionResponse:
    """
    Create a new collection for the current user.

    Args:
        request: Collection creation data
        db: Database session
        user: Current authenticated user

    Returns:
        CollectionResponse: The created collection

    Raises:
        HTTPException: If collection creation fails
    """
    collection = Collection(
        user_id=user.id,
        name=request.name,
        description=request.description
    )

    db.add(collection)
    db.commit()
    db.refresh(collection)

    return CollectionResponse.from_orm(collection)


@router.get('/', response_model=dict)
async def list_collections(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """
    List all collections for the current user.

    Args:
        skip: Number of collections to skip
        limit: Number of collections to return
        db: Database session
        user: Current authenticated user

    Returns:
        dict: Total count and list of collections
    """
    total = db.query(Collection).filter(Collection.user_id == user.id).count()
    collections = db.query(Collection).filter(
        Collection.user_id == user.id
    ).offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [CollectionResponse.from_orm(c) for c in collections]
    }


@router.get('/{collection_id}', response_model=CollectionDetailResponse)
async def get_collection(
    collection_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CollectionDetailResponse:
    """
    Get a specific collection with all its books.

    Args:
        collection_id: ID of the collection
        db: Database session
        user: Current authenticated user

    Returns:
        CollectionDetailResponse: The collection with its books

    Raises:
        HTTPException: If collection not found or user doesn't own it
    """
    collection = db.query(Collection).filter(
        Collection.id == collection_id
    ).first()

    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection {collection_id} not found"
        )

    # Check ownership
    if collection.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this collection"
        )

    # Get books in collection
    collection_books = db.query(CollectionBook).filter(
        CollectionBook.collection_id == collection_id
    ).all()

    books = []
    for cb in collection_books:
        book = db.query(Book).filter(Book.id == cb.book_id).first()
        if book:
            books.append(BookSearchResponse.from_orm(book))

    response = CollectionDetailResponse.from_orm(collection)
    response.books = books
    return response


@router.post('/{collection_id}/books', status_code=status.HTTP_201_CREATED)
async def add_book_to_collection(
    collection_id: int,
    book_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """
    Add a book to a collection.

    Args:
        collection_id: ID of the collection
        book_id: ID of the book to add
        db: Database session
        user: Current authenticated user

    Returns:
        dict: Success status

    Raises:
        HTTPException: If collection/book not found, user doesn't own collection, or book already in collection
    """
    # Verify collection exists and belongs to user
    collection = db.query(Collection).filter(
        Collection.id == collection_id
    ).first()

    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection {collection_id} not found"
        )

    if collection.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this collection"
        )

    # Verify book exists
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book {book_id} not found"
        )

    # Check if book already in collection
    existing = db.query(CollectionBook).filter(
        CollectionBook.collection_id == collection_id,
        CollectionBook.book_id == book_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Book is already in this collection"
        )

    # Add book to collection
    collection_book = CollectionBook(
        collection_id=collection_id,
        book_id=book_id
    )

    db.add(collection_book)
    db.commit()

    return {"status": "book added"}


@router.delete('/{collection_id}/books/{book_id}', status_code=status.HTTP_204_NO_CONTENT)
async def remove_book_from_collection(
    collection_id: int,
    book_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """
    Remove a book from a collection.

    Args:
        collection_id: ID of the collection
        book_id: ID of the book to remove
        db: Database session
        user: Current authenticated user

    Raises:
        HTTPException: If collection not found, user doesn't own it, or book not in collection
    """
    # Verify collection exists and belongs to user
    collection = db.query(Collection).filter(
        Collection.id == collection_id
    ).first()

    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection {collection_id} not found"
        )

    if collection.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this collection"
        )

    # Find and delete the collection book
    collection_book = db.query(CollectionBook).filter(
        CollectionBook.collection_id == collection_id,
        CollectionBook.book_id == book_id
    ).first()

    if not collection_book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book is not in this collection"
        )

    db.delete(collection_book)
    db.commit()
