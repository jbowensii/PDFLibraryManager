# PDF Library Manager (PDF-LM) — MVP Implementation Plan

> **For agentic workers:** Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a self-hosted PDF library server with OCR, metadata enrichment, duplicate detection, and multi-user access—MVP scope as defined in the design spec.

**Architecture:** 
- **Layered backend:** FastAPI routes → services → domain logic → database
- **Async processing:** Celery workers for OCR, metadata lookup, duplicate scanning
- **React frontend:** Component-based UI with Material-UI, consuming REST API
- **Local-first storage:** PDFs remain on user's filesystem; app indexes and enriches metadata

**Tech Stack:** Python 3.11 + FastAPI, PostgreSQL, Redis, Celery, React 18 + TypeScript, Docker Compose

## Global Constraints

- **Python version:** 3.11+
- **Node.js:** 18+
- **PostgreSQL:** 14+
- **Database:** 100K+ book entries must scale (indexes, GIN for full-text search)
- **OCR workers:** User-configurable 1-5 concurrent (default 3)
- **File storage:** Support local, NAS, cloud mounts (all via filesystem path)
- **Naming template:** User-configurable with smart variable substitution
- **Metadata confidence threshold:** 0.9 for auto-apply, < 0.9 asks user
- **Duplicate resolution:** Auto-delete if OCR error diff ≥ 20%, else manual review
- **Permissions:** Three roles only (Admin, Curator, Viewer)
- **Testing:** TDD approach, pytest for backend, Jest for frontend

---

## Phase 1: Backend Foundation (Sequential)

### Task 1: Database Models & Schema

**Files:**
- Create: `src/backend/app/models.py`
- Create: `src/backend/app/schemas.py`
- Modify: `src/backend/app/database.py` (add metadata/indexes)
- Test: `src/backend/tests/test_models.py`

**Interfaces:**
- Produces: SQLAlchemy ORM models (`User`, `Book`, `Collection`, `Job`, `DuplicateCandidate`)
- Produces: Pydantic schemas for API responses (`BookResponse`, `UserResponse`, etc.)

**Detailed Steps:**

- [ ] **Step 1: Write test for User model**

```python
# src/backend/tests/test_models.py
import pytest
from app.models import User
from app.database import SessionLocal

def test_user_creation():
    """Test creating a user."""
    db = SessionLocal()
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash="hashed_password",
        role="curator"
    )
    db.add(user)
    db.commit()
    
    fetched = db.query(User).filter_by(username="testuser").first()
    assert fetched.email == "test@example.com"
    assert fetched.role == "curator"
    
    db.delete(user)
    db.commit()
    db.close()
```

- [ ] **Step 2: Implement User model**

```python
# src/backend/app/models.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, CheckConstraint
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(
        String(50),
        nullable=False,
        index=True,
        default="viewer",
        server_default="viewer"
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    collections = relationship("Collection", back_populates="user", cascade="all, delete-orphan")
    reading_status = relationship("ReadingStatus", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'curator', 'viewer')"),
    )
```

- [ ] **Step 3: Implement Book model with indexes**

```python
# Add to src/backend/app/models.py
from sqlalchemy import ForeignKey, Boolean, Float, LargeBinary, Text
from sqlalchemy.types import TSVECTOR

class Book(Base):
    __tablename__ = "books"
    
    id = Column(Integer, primary_key=True)
    filesystem_path = Column(String(4096), unique=True, nullable=False, index=True)
    filename_normalized = Column(String(1024))
    
    # Metadata
    title = Column(String(1024), index=True)
    publisher = Column(String(500), index=True)
    author = Column(String(500), index=True)
    game_name = Column(String(500))
    isbn = Column(String(20), index=True)
    product_number = Column(String(100))
    publication_date = Column(DateTime)
    
    # OCR & text
    has_embedded_text = Column(Boolean, default=False)
    ocr_status = Column(String(50), default="pending", index=True)
    ocr_error_count = Column(Integer, default=0)
    ocr_language = Column(String(10), default="eng")
    full_text_index = Column(TSVECTOR)
    
    # Quality metrics
    file_size_bytes = Column(Integer)
    page_count = Column(Integer)
    ocr_engine = Column(String(50))
    ocr_confidence = Column(Float)
    
    # Metadata enrichment
    cover_image_local_path = Column(String(4096))
    cover_image_blob = Column(LargeBinary)
    metadata_source = Column(String(100))
    metadata_confidence = Column(Float, default=0.0)
    metadata_locked = Column(Boolean, default=False)
    
    # Deduplication
    content_hash = Column(String(64))
    is_duplicate = Column(Boolean, default=False, index=True)
    duplicate_parent_id = Column(Integer, ForeignKey("books.id"))
    
    # Timestamps
    date_added = Column(DateTime, default=datetime.utcnow)
    date_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    date_last_scanned = Column(DateTime)
    
    __table_args__ = (
        CheckConstraint("ocr_confidence >= 0 AND ocr_confidence <= 1"),
        CheckConstraint("metadata_confidence >= 0 AND metadata_confidence <= 1"),
    )
```

- [ ] **Step 4: Implement remaining models (Collection, Job, DuplicateCandidate)**

```python
# Add to src/backend/app/models.py
class Collection(Base):
    __tablename__ = "collections"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    is_shared = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="collections")
    books = relationship("Book", secondary="collection_books", viewonly=True)
    
    __table_args__ = (
        UniqueConstraint("user_id", "name"),
    )

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True)
    job_type = Column(String(100), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"))
    status = Column(String(50), default="queued", index=True)
    progress_percent = Column(Integer, default=0)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=2)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    paused_at = Column(DateTime)
    
    __table_args__ = (
        CheckConstraint("progress_percent >= 0 AND progress_percent <= 100"),
    )

class DuplicateCandidate(Base):
    __tablename__ = "duplicate_candidates"
    
    id = Column(Integer, primary_key=True)
    book_id_1 = Column(Integer, ForeignKey("books.id"))
    book_id_2 = Column(Integer, ForeignKey("books.id"))
    similarity_score = Column(Float)
    metadata_match_score = Column(Float)
    ocr_error_diff = Column(Integer)
    file_size_diff_percent = Column(Float)
    status = Column(String(50), default="pending", index=True)
    user_decision_by = Column(Integer, ForeignKey("users.id"))
    resolved_at = Column(DateTime)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
```

- [ ] **Step 5: Write Pydantic schemas**

```python
# src/backend/app/schemas.py
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "viewer"

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class BookCreate(BaseModel):
    title: str
    author: Optional[str] = None
    publisher: Optional[str] = None
    isbn: Optional[str] = None
    filesystem_path: str

class BookResponse(BaseModel):
    id: int
    title: str
    author: Optional[str]
    publisher: Optional[str]
    isbn: Optional[str]
    filesystem_path: str
    ocr_status: str
    metadata_confidence: float
    cover_image_local_path: Optional[str]
    date_added: datetime
    
    class Config:
        from_attributes = True

class JobResponse(BaseModel):
    id: int
    job_type: str
    status: str
    progress_percent: int
    created_at: datetime
    
    class Config:
        from_attributes = True
```

- [ ] **Step 6: Run test to verify it passes**

```bash
cd src/backend
pytest tests/test_models.py -v
```

Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
git add src/backend/app/models.py src/backend/app/schemas.py src/backend/tests/test_models.py
git commit -m "feat: implement database models and Pydantic schemas for MVP"
```

---

### Task 2: Authentication & JWT

**Files:**
- Create: `src/backend/app/auth/jwt_handler.py`
- Create: `src/backend/app/auth/password.py`
- Create: `src/backend/app/api/auth.py`
- Test: `src/backend/tests/test_api/test_auth.py`

**Interfaces:**
- Consumes: `User` model from Task 1, `config.settings`
- Produces: JWT token generation/validation, password hashing, `/api/v1/auth/login`, `/api/v1/auth/register`

**Detailed Steps:**

- [ ] **Step 1: Write failing test for password hashing**
- [ ] **Step 2: Implement password utilities**
- [ ] **Step 3: Write failing test for JWT**
- [ ] **Step 4: Implement JWT handler**
- [ ] **Step 5: Write failing test for login endpoint**
- [ ] **Step 6: Implement auth endpoints**
- [ ] **Step 7: Add auth router to main.py**
- [ ] **Step 8: Run tests**
- [ ] **Step 9: Commit**

---

### Task 3: Core Book CRUD API

**Files:**
- Create: `src/backend/app/services/book_service.py`
- Create: `src/backend/app/api/books.py`
- Test: `src/backend/tests/test_api/test_books.py`

**Interfaces:**
- Consumes: `Book`, `User` models; `BookResponse` schema; auth endpoints
- Produces: `GET /api/v1/books`, `GET /api/v1/books/{id}`, `PATCH /api/v1/books/{id}`, `DELETE /api/v1/books/{id}`, `BookService` class

---

## Phase 2: OCR Pipeline & Metadata Services

### Task 4: OCR Pipeline Core

### Task 5: Metadata Matching & Lookup Service

### Task 6: Duplicate Detection Engine

---

## Phase 3: Frontend UI

### Task 7: React Setup & Core Components

---

## Phase 4: Integration & Testing

### Task 8: Library Scan Endpoint & Job Queue

### Task 9: Docker Compose Local Development Testing

### Task 10: Remaining API Endpoints & Frontend Pages

---

## Summary

**Total Tasks:** 10 core tasks

**Phase Breakdown:**
- Phase 1 (Sequential): Tasks 1-3 — ~2-3 days
- Phase 2 (Parallel): Tasks 4-6 — ~3-4 days
- Phase 3 (Parallel with 2): Task 7 — ~2-3 days
- Phase 4 (Sequential after 2): Tasks 8-9 — ~2-3 days
- Task 10+: Remaining endpoints — ~5-7 days

**Total Estimate:** 15-20 days for MVP
