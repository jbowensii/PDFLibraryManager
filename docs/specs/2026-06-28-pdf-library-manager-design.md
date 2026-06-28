# PDF Library Manager (PDF-LM) — Technical Design Specification

**Date:** 2026-06-28  
**Version:** 1.0 (MVP)  
**Status:** Approved for Implementation  
**Author:** John Bowens (via Claude Code)  

---

## Executive Summary

PDF Library Manager is a self-hosted server for organizing, indexing, and browsing PDF game manuals/guides with intelligent OCR, metadata enrichment, and duplicate detection. It provides a Jellyfin/Plex-like experience for PDF libraries, allowing multi-user access with role-based permissions.

**Key Features:**
- Conditional multi-pass OCR (Tesseract + PaddleOCR) for scanned PDFs
- Automated metadata extraction and enrichment via Google Books/Open Library APIs
- User-configurable file naming and directory organization
- Intelligent duplicate detection and resolution
- Web-based UI with search, browsing, collections, and admin controls
- REST API for programmatic access
- Docker deployment (Unraid-compatible)

---

## 1. Architecture Overview

### 1.1 Three-Tier System

```
┌─────────────────────────────────────┐
│   Web Browser (React Frontend)      │
│   - Browse, search, manage library  │
│   - Admin operations                │
└──────────────┬──────────────────────┘
               │ HTTPS
┌──────────────▼──────────────────────┐
│   FastAPI Backend (Python)          │
│   - REST API                        │
│   - OCR pipeline worker             │
│   - Metadata matching               │
│   - Duplicate detection             │
│   - File organization               │
└──────────────┬──────────────────────┘
               │
      ┌────────┴────────┐
      │                 │
   PostgreSQL         Redis
  (metadata,      (task queue,
   auth, jobs)     caching)
```

### 1.2 Data Flow Pipeline

```
New PDFs (Intake Dir)
    ↓ [Library Scan Job]
[1] Text Detection (pdfplumber)
    ↓
    ├─→ Has embedded text? → Skip OCR
    │
    └─→ No text → [2] Multi-Pass OCR
           ├─→ Tesseract (fast)
           └─→ PaddleOCR (if confidence < 70%)
    ↓ [3] Error Counting
    ├─→ Detect [?] and gibberish patterns
    └─→ Store error count for dedup scoring
    ↓ [4] Text Embedding
    └─→ Embed OCR text back into PDF
    ↓ [5] Metadata Extraction
    ├─→ Parse title, author, ISBN, dates from PDF
    └─→ Store in database
    ↓ [6] Metadata Lookup
    ├─→ Try ISBN lookup (most reliable)
    ├─→ Try product number lookup
    └─→ Try fuzzy title+author match
    ↓ [7] Confidence Check
    ├─→ Confidence >= 90%? → Auto-apply
    └─→ Confidence < 90%? → Ask user
    ↓ [8] Duplicate Detection
    ├─→ Find similar books by metadata
    ├─→ Score by title/author/ISBN/OCR quality
    └─→ Auto-resolve if >= 20% error difference, else ask user
    ↓ [9] File Organization
    ├─→ Generate filename per user template
    │   {Publisher}/{Game}/{Game Name} {Title} - {ISBN} - {Date}.pdf
    └─→ Move to organized directory structure
    ↓ [10] Database Indexing
    ├─→ Index in PostgreSQL
    ├─→ Add full-text search index
    └─→ Generate cover image thumbnail
    ↓
    Web UI displays organized library
```

---

## 2. Technology Stack

| Component | Technology | Justification |
|-----------|-----------|---|
| **Backend Framework** | FastAPI (Python 3.11+) | Modern, async, auto-generates OpenAPI docs |
| **Database** | PostgreSQL 14+ | Mature, full-text search (GIN indexes), scales to 100K+ entries |
| **Task Queue** | Celery + Redis | Async job processing, pause/resume, retry logic |
| **OCR** | Tesseract + PaddleOCR | Battle-tested; Tesseract fast, PaddleOCR high accuracy |
| **PDF Manipulation** | PyPDF2, pdfplumber, pymupdf | Text extraction, text layer embedding, manipulation |
| **Image Processing** | OpenCV, Pillow | Preprocessing (deskew, denoise, binarize) |
| **Metadata Lookup** | Google Books API, Open Library API | Comprehensive coverage, free tier sufficient |
| **Frontend Framework** | React 18 + TypeScript | Modern, type-safe, rich component ecosystem |
| **UI Library** | shadcn/ui (or Material-UI) | Component library, Jellyfin-like styling |
| **Fuzzy Matching** | fuzzywuzzy, difflib | Robust string similarity for metadata matching |
| **Containerization** | Docker + Docker Compose | Unraid-compatible, reproducible environment |
| **Web Server** | Gunicorn (prod), Uvicorn (dev) | Production-grade WSGI/ASGI |
| **Authentication** | JWT (PyJWT) | Stateless, scalable |

---

## 3. Database Schema

### 3.1 Core Tables

**users** — User accounts and roles
```sql
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(255) UNIQUE NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(50) NOT NULL, -- 'admin', 'curator', 'viewer'
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**books** — PDF metadata and processing status
```sql
CREATE TABLE books (
  id SERIAL PRIMARY KEY,
  filesystem_path VARCHAR(4096) NOT NULL UNIQUE,
  filename_normalized VARCHAR(1024),
  
  -- Metadata
  title VARCHAR(1024),
  publisher VARCHAR(500),
  author VARCHAR(500),
  game_name VARCHAR(500),
  isbn VARCHAR(20),
  product_number VARCHAR(100),
  publication_date DATE,
  
  -- OCR & text
  has_embedded_text BOOLEAN DEFAULT FALSE,
  ocr_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'in_progress', 'completed', 'failed'
  ocr_error_count INT DEFAULT 0,
  ocr_language VARCHAR(10) DEFAULT 'eng',
  full_text_index TSVECTOR,
  
  -- Quality
  file_size_bytes BIGINT,
  page_count INT,
  ocr_engine VARCHAR(50),
  ocr_confidence FLOAT,
  
  -- Metadata enrichment
  cover_image_local_path VARCHAR(4096),
  cover_image_blob BYTEA,
  metadata_source VARCHAR(100), -- 'google_books', 'open_library', 'manual'
  metadata_confidence FLOAT DEFAULT 0.0,
  metadata_locked BOOLEAN DEFAULT FALSE,
  
  -- Deduplication
  content_hash VARCHAR(64),
  is_duplicate BOOLEAN DEFAULT FALSE,
  duplicate_parent_id INT REFERENCES books(id),
  
  -- Timestamps
  date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  date_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  date_last_scanned TIMESTAMP,
  
  INDEX idx_filesystem_path (filesystem_path),
  INDEX idx_title (title),
  INDEX idx_isbn (isbn),
  INDEX idx_ocr_status (ocr_status),
  INDEX idx_full_text (full_text_index) USING GIN
);
```

**collections** — User-curated shelves/lists
```sql
CREATE TABLE collections (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id) NOT NULL,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  is_shared BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (user_id, name)
);

CREATE TABLE collection_books (
  collection_id INT REFERENCES collections(id) ON DELETE CASCADE,
  book_id INT REFERENCES books(id) ON DELETE CASCADE,
  added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (collection_id, book_id)
);
```

**jobs** — Background task tracking
```sql
CREATE TABLE jobs (
  id SERIAL PRIMARY KEY,
  job_type VARCHAR(100) NOT NULL, -- 'ocr', 'metadata_scan', 'dedup', 'organize'
  book_id INT REFERENCES books(id),
  status VARCHAR(50) DEFAULT 'queued', -- 'queued', 'in_progress', 'completed', 'failed', 'paused'
  progress_percent INT DEFAULT 0,
  error_message TEXT,
  retry_count INT DEFAULT 0,
  max_retries INT DEFAULT 2,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  paused_at TIMESTAMP,
  INDEX idx_status (status)
);
```

**duplicate_candidates** — Suspected duplicates for manual review
```sql
CREATE TABLE duplicate_candidates (
  id SERIAL PRIMARY KEY,
  book_id_1 INT REFERENCES books(id),
  book_id_2 INT REFERENCES books(id),
  similarity_score FLOAT, -- 0-1
  metadata_match_score FLOAT,
  ocr_error_diff INT,
  file_size_diff_percent FLOAT,
  status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'resolved_keep_1', 'resolved_keep_2', 'keep_both'
  user_decision_by INT REFERENCES users(id),
  resolved_at TIMESTAMP,
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_status (status)
);
```

---

## 4. OCR Pipeline (Detailed)

### 4.1 Phase 1: Text Detection

```python
def check_has_embedded_text(pdf_path: str, threshold: int = 500) -> bool:
    """Check if PDF already has extractable text."""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if len(text.strip()) > threshold:
                return True
    return False
```

**Outcome:**
- If `True` → Store in DB, skip OCR, extract full text for search index
- If `False` → Proceed to OCR

### 4.2 Phase 2: Multi-Pass OCR (Conditional)

**Pass 1: Tesseract (fast baseline)**
```
For each page:
  1. Load image
  2. Preprocess (deskew, denoise, binarize)
  3. Run Tesseract
  4. Count OCR errors (look for [?], gibberish)
  5. Get confidence score
```

**Pass 2: PaddleOCR (if needed)**
```
If Tesseract confidence < 70% OR error_count > threshold:
  1. Run PaddleOCR
  2. Count errors, get confidence
  3. Compare with Pass 1
  4. Keep winner (fewer errors + higher confidence)
```

### 4.3 Phase 3: Error Detection

```python
def count_ocr_errors(text: str) -> int:
    """Count undetermined/gibberish characters."""
    errors = 0
    errors += len(re.findall(r'\[?\?\]?', text))  # [?] markers
    errors += len(re.findall(r'[^\x20-\x7E\n]', text))  # non-ASCII
    errors += len(re.findall(r'[ ]{5,}', text))  # excessive spaces
    return errors
```

### 4.4 Phase 4: Text Embedding

```python
def embed_text_in_pdf(pdf_path: str, ocr_text_per_page: dict) -> None:
    """Create new PDF with OCR text layer."""
    # Use pymupdf or PyPDF2 to create text layer
    # Replace original file (preserves filesystem_path)
```

### 4.5 Job State Machine

```
PENDING
    ↓ [start]
IN_PROGRESS → [pause] → PAUSED
    ↓ [resume]
    ├─→ [success] → COMPLETED
    ├─→ [failure] → [retry?]
           ├─→ [yes, < max_retries] → IN_PROGRESS
           └─→ [no] → FAILED
    └─→ [cancel] → CANCELLED
```

**Pause/Resume:** Store current page number; on resume, start from that page.

---

## 5. Metadata Matching Algorithm

### 5.1 Extraction from PDF

```python
def extract_metadata(pdf_path: str) -> dict:
    """Extract basic metadata from PDF."""
    with pdfplumber.open(pdf_path) as pdf:
        metadata = {
            'title': pdf.metadata.get('title', ''),
            'author': pdf.metadata.get('author', ''),
            'isbn': extract_isbn(pdf),
            'product_number': extract_product_number(pdf),
            'publication_date': extract_date(pdf),
        }
    return metadata
```

### 5.2 Lookup Chain

**Priority:**
1. **ISBN lookup** (most reliable) → Open Library API
2. **Product number lookup** → Open Library search
3. **Fuzzy title+author match** → Google Books API

### 5.3 Confidence Scoring

```python
def calculate_confidence(extracted: dict, api_result: dict) -> float:
    """
    Returns 0-1 score.
    >= 0.9: auto-apply
    < 0.9: ask user
    """
    title_sim = fuzz.token_set_ratio(extracted['title'], api_result['title']) / 100
    author_sim = fuzz.token_set_ratio(extracted['author'], api_result['author']) / 100
    overall = (title_sim * 0.6) + (author_sim * 0.4)
    return overall
```

### 5.4 User Override

Users can manually edit any metadata field in the web UI post-import. Setting `metadata_locked = TRUE` prevents re-matching on future scans.

---

## 6. Duplicate Detection

### 6.1 Detection Strategy

**Candidate identification** (broad net):
```sql
SELECT book_b.* FROM books book_b
WHERE book_b.publisher = $1
  AND similarity(book_b.title, $2) > 0.7
  AND book_b.id != $3;
```

**Detailed scoring** (composite):
```python
def duplicate_score(book_a, book_b):
    metadata_score = similarity(title) * 0.5 + similarity(author) * 0.3 + similarity(pub) * 0.2
    isbn_score = 1.0 if isbn_match else 0.5 if both_missing else 0.2
    quality_score = 1.0 - (error_diff / max_error_count)
    overall = (metadata_score * 0.4) + (isbn_score * 0.2) + (quality_score * 0.3)
    return overall
```

### 6.2 Resolution Logic

```
if score > 0.95:
    → AUTO-DELETE loser (higher OCR error count)

elif score > 0.75:
    error_diff_percent = (error_diff / max_error_count) * 100
    if error_diff_percent >= 20:
        → AUTO-DELETE loser
    else:
        → MANUAL REVIEW (close call)

elif score > 0.5:
    → MANUAL REVIEW (low confidence)

else:
    → Not a duplicate
```

---

## 7. File Organization

### 7.1 User-Configurable Templates

```
Default: {Publisher}/{Game}/{Game Name} {Title} - {ISBN} - {Publication Date}

Example output (with ISBN):
/mnt/PDFGameVault/Blizzard Entertainment/StarCraft/StarCraft Battle Chest Manual - 1234567890 - 2000-12-31.pdf

Example output (without ISBN):
/mnt/PDFGameVault/Blizzard Entertainment/StarCraft/StarCraft Battle Chest Manual - 1999-11-30.pdf
```

**Smart separator stripping:** If a variable is empty, don't leave trailing `-` separators.

### 7.2 Root Path Flexibility

Supports:
- Local: `/home/user/PDFGameVault`
- NAS mount: `/mnt/nas/PDFGameVault`
- Cloud mount: `/mnt/cloud/PDFGameVault` (rclone, etc.)

Stored in `library_config.root_path` (user preference).

---

## 8. REST API

### 8.1 Authentication

```
POST /api/v1/auth/login
  → Returns JWT token (Bearer header for all subsequent requests)
```

### 8.2 Core Endpoints

**Books:**
```
GET    /api/v1/books                    -- List (paginated, filterable)
GET    /api/v1/books/{id}               -- Detail
PATCH  /api/v1/books/{id}               -- Update metadata
DELETE /api/v1/books/{id}               -- Delete (admin only)
GET    /api/v1/books/{id}/download      -- Download PDF
```

**Library Operations:**
```
POST   /api/v1/library/scan             -- Trigger scan
GET    /api/v1/library/scan/{job_id}    -- Get progress
POST   /api/v1/library/scan/{job_id}/pause   -- Pause
POST   /api/v1/library/scan/{job_id}/resume  -- Resume
PATCH  /api/v1/library/config           -- Update config
```

**Duplicates:**
```
GET    /api/v1/duplicates               -- List candidates
POST   /api/v1/duplicates/{id}/resolve  -- Resolve (keep_1, keep_2, keep_both)
```

**Collections:**
```
POST   /api/v1/collections              -- Create
GET    /api/v1/collections              -- List user's
POST   /api/v1/collections/{id}/books   -- Add book
DELETE /api/v1/collections/{id}/books/{book_id} -- Remove
```

---

## 9. Development Environment

### 9.1 Docker Compose (Local Dev)

Services:
- **postgres** — Database (hot-reload safe, persisted data)
- **redis** — Task queue & caching
- **backend** — FastAPI (hot-reload on code changes)
- **celery** — Background worker (hot-reload safe)
- **frontend** — React (hot-reload, npm start)

**Key features:**
- All services auto-restart on failure
- Health checks (postgres waits before backend starts)
- Shared test library volume for test PDFs
- Environment variables from `.env.dev`

### 9.2 Project Structure (VS Code Workspace)

```
PDFLibraryManager.code-workspace
├── Backend (Python)
│   └── src/backend/
├── Frontend (React)
│   └── src/frontend/
└── Documentation
    └── docs/
```

### 9.3 Getting Started

```bash
# 1. Clone repo
git clone https://github.com/jbowensii/PDFLibraryManager.git
cd PDFLibraryManager

# 2. Open in VS Code
code PDFLibraryManager.code-workspace

# 3. Start dev environment
docker-compose -f docker-compose.dev.yml up

# 4. Access:
# Frontend:  http://localhost:3000
# API Docs:  http://localhost:8000/docs
# Postgres:  localhost:5432 (user: dev, pass: devpass)
```

---

## 10. Testing Strategy

### 10.1 Unit Tests
- OCR error detection
- Metadata matching fuzzy logic
- Duplicate scoring algorithm
- Template variable substitution

**Framework:** pytest (Python), Jest (React)

### 10.2 Integration Tests
- Full library scan pipeline (intake → organize → index)
- API endpoints (with test database)
- Duplicate detection end-to-end

### 10.3 E2E Tests
- User login → browse → search → create collection
- Admin scan → review duplicates → resolve
- OCR progress monitoring

**Framework:** Playwright (browser automation)

---

## 11. Deployment

### 11.1 Production Docker Images

**Backend Dockerfile (multi-stage):**
```dockerfile
FROM python:3.11-slim AS builder
# Install dependencies

FROM python:3.11-slim
# Copy built artifacts
EXPOSE 8000
CMD ["gunicorn", "app.main:app", "-w", "4", "-b", "0.0.0.0:8000"]
```

### 11.2 Unraid Docker Compose

```yaml
services:
  postgres:
    image: postgres:14-alpine
    volumes:
      - /mnt/user/appdata/pdf-lm/postgres:/var/lib/postgresql/data

  backend:
    image: ghcr.io/jbowensii/pdf-lm-backend:latest
    ports:
      - "8000:8000"
    volumes:
      - /mnt/user/PDFGameVault:/library  # User's actual library
      - /mnt/user/appdata/pdf-lm/uploads:/app/uploads

  frontend:
    image: ghcr.io/jbowensii/pdf-lm-frontend:latest
    ports:
      - "3000:3000"
```

---

## 12. MVP Scope

✅ **Included:**
- Multi-user auth (admin, curator, viewer)
- Library scanning + PDF intake
- Conditional OCR (Tesseract + PaddleOCR)
- Metadata extraction + Google Books/Open Library lookup
- File renaming + organization (user-configurable)
- Duplicate detection + manual resolution
- Web UI (search, browse, collections)
- REST API (full CRUD)
- Docker deployment

❌ **Not MVP (v2 later):**
- Advanced analytics (reading stats)
- Social features (recommendations, follow users)
- Mobile app
- Batch operations
- Comic/manga support
- Multi-language OCR
- WebDAV integration

---

## 13. Success Criteria

- [x] Design approved
- [ ] Local dev environment runs without errors
- [ ] Backend tests: > 80% coverage
- [ ] Frontend loads without errors
- [ ] Library scan completes on test PDF set (10-50 PDFs)
- [ ] OCR pipeline produces searchable PDFs
- [ ] Metadata matching works for 90%+ of test books
- [ ] Duplicates correctly identified and user can resolve
- [ ] Web UI matches Jellyfin/Plex look & feel
- [ ] Docker images build and run on Unraid
- [ ] All endpoints documented and functional

---

**Approved:** John Bowens, 2026-06-28
