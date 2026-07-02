"""
Pydantic schemas for API requests and responses.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class JobResponse(BaseModel):
    """Response schema for job status."""

    id: int
    type: str
    status: str
    progress_percent: int
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    class Config:
        from_attributes = True


class BookResponse(BaseModel):
    """Response schema for book details."""

    id: int
    title: str
    author: str
    publisher: str
    isbn: Optional[str] = None
    ocr_status: str
    has_embedded_text: bool
    filename_normalized: Optional[str] = None

    class Config:
        from_attributes = True


class BookDetailResponse(BookResponse):
    """Detailed response schema for a single book."""

    content_hash: Optional[str] = None
    ocr_error_count: int
    is_duplicate: bool
    duplicate_parent_id: Optional[int] = None
    filesystem_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class BookSearchResponse(BaseModel):
    """Response schema for book search results."""

    id: int
    title: str
    author: str
    publisher: str
    isbn: Optional[str] = None

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """Request schema for creating a new user."""

    username: str
    email: str
    password: str


class UserUpdate(BaseModel):
    """Request schema for updating user information."""

    role: Optional[str] = None


class UserResponse(BaseModel):
    """Response schema for user information."""

    id: int
    username: str
    email: str
    role: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Response schema for listing users."""

    id: int
    username: str
    email: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class CollectionCreate(BaseModel):
    """Request schema for creating a collection."""

    name: str
    description: Optional[str] = None


class CollectionResponse(BaseModel):
    """Response schema for a collection."""

    id: int
    user_id: int
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CollectionDetailResponse(CollectionResponse):
    """Detailed response schema for a collection with books."""

    books: List[BookSearchResponse] = []


class DuplicateCandidateResponse(BaseModel):
    """Response schema for a duplicate candidate pair."""

    id: int
    book_id_1: int
    book_id_2: int
    similarity_score: float
    status: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DuplicateResolveRequest(BaseModel):
    """Request schema for resolving a duplicate candidate."""

    keep_book_id: int


class SearchRequest(BaseModel):
    """Request schema for searching books."""

    q: str
    search_type: Optional[str] = 'title'  # title, author, publisher
    limit: Optional[int] = 20


class SearchResponse(BaseModel):
    """Response schema for search results."""

    total: int
    items: List[BookSearchResponse]


class AuditLogResponse(BaseModel):
    """Response schema for audit log entries."""

    id: int
    user_id: Optional[int] = None
    action: str
    details: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ScanRequest(BaseModel):
    """Request schema for starting a library scan."""

    source_dir: Optional[str] = None


class ScanResponse(BaseModel):
    """Response schema for scan start."""

    status: str
    pdfs_queued: int
