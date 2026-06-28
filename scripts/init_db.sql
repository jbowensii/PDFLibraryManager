-- PDF Library Manager Database Initialization Script
-- This script is automatically run when the postgres container starts

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- For fuzzy string matching
CREATE EXTENSION IF NOT EXISTS unaccent;  -- For accent-insensitive search

-- Users table
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(255) UNIQUE NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(50) NOT NULL CHECK (role IN ('admin', 'curator', 'viewer')),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- Library configuration
CREATE TABLE IF NOT EXISTS library_config (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  root_path VARCHAR(4096) NOT NULL,
  naming_template VARCHAR(1024) DEFAULT '{Publisher}/{Game}/{Game Name} {Title} - {ISBN} - {Publication Date}',
  max_ocr_workers INT DEFAULT 3,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_library_config_user ON library_config(user_id);

-- Books table
CREATE TABLE IF NOT EXISTS books (
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
  ocr_status VARCHAR(50) DEFAULT 'pending' CHECK (ocr_status IN ('pending', 'in_progress', 'completed', 'failed', 'skipped')),
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
  metadata_source VARCHAR(100),
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

  CONSTRAINT valid_ocr_confidence CHECK (ocr_confidence >= 0 AND ocr_confidence <= 1),
  CONSTRAINT valid_metadata_confidence CHECK (metadata_confidence >= 0 AND metadata_confidence <= 1)
);

CREATE INDEX idx_books_filesystem_path ON books(filesystem_path);
CREATE INDEX idx_books_title ON books(title);
CREATE INDEX idx_books_author ON books(author);
CREATE INDEX idx_books_publisher ON books(publisher);
CREATE INDEX idx_books_isbn ON books(isbn);
CREATE INDEX idx_books_ocr_status ON books(ocr_status);
CREATE INDEX idx_books_is_duplicate ON books(is_duplicate);
CREATE INDEX idx_books_full_text ON books USING GIN(full_text_index);

-- Collections (shelves)
CREATE TABLE IF NOT EXISTS collections (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id) NOT NULL,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  is_shared BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (user_id, name)
);

CREATE INDEX idx_collections_user ON collections(user_id);

-- Collection books (many-to-many)
CREATE TABLE IF NOT EXISTS collection_books (
  collection_id INT REFERENCES collections(id) ON DELETE CASCADE,
  book_id INT REFERENCES books(id) ON DELETE CASCADE,
  added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (collection_id, book_id)
);

CREATE INDEX idx_collection_books_book ON collection_books(book_id);

-- Reading status
CREATE TABLE IF NOT EXISTS reading_status (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id) NOT NULL,
  book_id INT REFERENCES books(id) NOT NULL,
  status VARCHAR(50) DEFAULT 'unread' CHECK (status IN ('unread', 'reading', 'completed')),
  rating INT CHECK (rating >= 1 AND rating <= 5),
  notes TEXT,
  date_started DATE,
  date_completed DATE,
  last_read TIMESTAMP,
  UNIQUE (user_id, book_id)
);

CREATE INDEX idx_reading_status_user ON reading_status(user_id);
CREATE INDEX idx_reading_status_book ON reading_status(book_id);
CREATE INDEX idx_reading_status_status ON reading_status(status);

-- Background jobs
CREATE TABLE IF NOT EXISTS jobs (
  id SERIAL PRIMARY KEY,
  job_type VARCHAR(100) NOT NULL,
  book_id INT REFERENCES books(id),
  status VARCHAR(50) DEFAULT 'queued' CHECK (status IN ('queued', 'in_progress', 'completed', 'failed', 'paused', 'cancelled')),
  progress_percent INT DEFAULT 0 CHECK (progress_percent >= 0 AND progress_percent <= 100),
  error_message TEXT,
  retry_count INT DEFAULT 0,
  max_retries INT DEFAULT 2,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  paused_at TIMESTAMP
);

CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_job_type ON jobs(job_type);
CREATE INDEX idx_jobs_book_id ON jobs(book_id);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);

-- Duplicate candidates
CREATE TABLE IF NOT EXISTS duplicate_candidates (
  id SERIAL PRIMARY KEY,
  book_id_1 INT REFERENCES books(id),
  book_id_2 INT REFERENCES books(id),
  similarity_score FLOAT CHECK (similarity_score >= 0 AND similarity_score <= 1),
  metadata_match_score FLOAT CHECK (metadata_match_score >= 0 AND metadata_match_score <= 1),
  ocr_error_diff INT,
  file_size_diff_percent FLOAT,
  status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'resolved_keep_1', 'resolved_keep_2', 'keep_both', 'manual_review')),
  user_decision_by INT REFERENCES users(id),
  resolved_at TIMESTAMP,
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_duplicate_candidates_status ON duplicate_candidates(status);
CREATE INDEX idx_duplicate_candidates_created_at ON duplicate_candidates(created_at);

-- Taxonomy (learned Publisher/Game/Genre hierarchy)
CREATE TABLE IF NOT EXISTS taxonomy (
  id SERIAL PRIMARY KEY,
  category VARCHAR(100) NOT NULL,
  name VARCHAR(500) NOT NULL,
  normalized_name VARCHAR(500),
  occurrence_count INT DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (category, normalized_name)
);

CREATE INDEX idx_taxonomy_category ON taxonomy(category);
CREATE INDEX idx_taxonomy_normalized_name ON taxonomy(normalized_name);

-- Audit log
CREATE TABLE IF NOT EXISTS audit_log (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  action VARCHAR(255),
  book_id INT REFERENCES books(id),
  old_value TEXT,
  new_value TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_log_user_action ON audit_log(user_id, action);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);

-- Permissions
CREATE TABLE IF NOT EXISTS book_permissions (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  book_id INT REFERENCES books(id),
  permission VARCHAR(50) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (user_id, book_id, permission)
);

CREATE INDEX idx_book_permissions_user ON book_permissions(user_id);
CREATE INDEX idx_book_permissions_book ON book_permissions(book_id);

-- Create default admin user (password: admin123 - CHANGE THIS!)
INSERT INTO users (username, email, password_hash, role)
VALUES (
  'admin',
  'admin@local',
  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5YmMxSUied.Em',  -- bcrypt hash for 'admin123'
  'admin'
) ON CONFLICT (username) DO NOTHING;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO dev;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO dev;
