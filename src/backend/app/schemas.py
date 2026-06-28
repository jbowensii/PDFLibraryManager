"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    username: str = Field(..., min_length=3, max_length=255, description="Unique username")
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")
    role: str = Field(default="viewer", description="User role: admin, curator, or viewer")


class UserResponse(BaseModel):
    """Schema for user response."""

    id: int
    username: str
    email: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class BookCreate(BaseModel):
    """Schema for creating a new book."""

    title: str = Field(..., min_length=1, max_length=500, description="Book title")
    author: Optional[str] = Field(None, max_length=255, description="Book author")
    publisher: Optional[str] = Field(None, max_length=255, description="Book publisher")
    isbn: Optional[str] = Field(None, max_length=20, description="ISBN number")
    filesystem_path: str = Field(..., min_length=1, max_length=1024, description="File system path to PDF")


class BookResponse(BaseModel):
    """Schema for book response."""

    id: int
    title: Optional[str]
    author: Optional[str]
    publisher: Optional[str]
    isbn: Optional[str]
    filesystem_path: str
    ocr_status: str
    metadata_confidence: Optional[float]
    cover_image_local_path: Optional[str]
    date_added: datetime

    class Config:
        from_attributes = True


class JobResponse(BaseModel):
    """Schema for job response."""

    id: int
    job_type: str
    status: str
    progress_percent: int
    created_at: datetime

    class Config:
        from_attributes = True


class DuplicateCandidateResponse(BaseModel):
    """Schema for duplicate candidate response."""

    id: int
    book_id_1: int
    book_id_2: int
    similarity_score: float
    metadata_match_score: Optional[float]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class CollectionResponse(BaseModel):
    """Schema for collection response."""

    id: int
    user_id: int
    name: str
    description: Optional[str]
    is_shared: bool
    created_at: datetime

    class Config:
        from_attributes = True
