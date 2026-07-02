"""
Library scanning service for discovering and processing PDFs.

Provides functionality to scan directories for PDF files, create Book entries,
and queue processing jobs.
"""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..models import Book, Job
from ..worker import process_pdf


class BookQueryParams(BaseModel):
    """Query parameters for book list endpoints."""

    page: int = 1
    limit: int = 20
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None
    ocr_status: Optional[str] = None


class ScanService:
    """Service for scanning directories and managing processing jobs."""

    @staticmethod
    def scan_directory(db: Session, directory: str, recursive: bool = True) -> int:
        """
        Scan a directory for PDF files and queue them for processing.

        Args:
            db: Database session
            directory: Directory path to scan
            recursive: If True, scan subdirectories (default True)

        Returns:
            Number of PDFs queued for processing
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            raise ValueError(f"Directory does not exist: {directory}")

        # Determine glob pattern
        pattern = "**/*.pdf" if recursive else "*.pdf"

        pdf_files = dir_path.glob(pattern)
        count = 0

        for pdf_file in pdf_files:
            # Skip if already in database
            existing = db.query(Book).filter(
                Book.filesystem_path == str(pdf_file)
            ).first()
            if existing:
                continue

            # Calculate content hash
            try:
                content_hash = ScanService._calculate_sha256(str(pdf_file))
            except Exception as e:
                # Skip files that can't be read
                continue

            # Get file size
            try:
                file_size = pdf_file.stat().st_size
            except Exception:
                file_size = 0

            # Create Book entry
            book = Book(
                title=pdf_file.stem,  # Use filename as default title
                author='',
                publisher='',
                filesystem_path=str(pdf_file),
                filename_normalized=pdf_file.name,
                ocr_status='pending',
                has_embedded_text=False,
                file_size_bytes=file_size,
                content_hash=content_hash,
            )
            db.add(book)
            db.commit()  # Commit to get book.id

            # Create Job entry
            job = Job(
                book_id=book.id,
                job_type='ocr',
                status='queued',
            )
            db.add(job)
            db.commit()  # Commit to get job.id

            # Queue the processing task
            task = process_pdf.delay(book.id, job.id)
            job.celery_task_id = task.id
            db.commit()

            count += 1

        return count

    @staticmethod
    def get_job_status(db: Session, job_id: int) -> Optional[dict]:
        """
        Get the status of a processing job.

        Args:
            db: Database session
            job_id: ID of the job

        Returns:
            Dictionary with job status or None if not found
        """
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None

        return {
            'id': job.id,
            'type': job.job_type,
            'status': job.status,
            'progress_percent': job.progress_percent,
            'error_message': job.error_message,
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
        }

    @staticmethod
    def pause_job(db: Session, job_id: int) -> None:
        """
        Pause a processing job.

        Args:
            db: Database session
            job_id: ID of the job to pause
        """
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = 'paused'
            job.paused_at = datetime.utcnow()
            db.commit()

    @staticmethod
    def resume_job(db: Session, job_id: int) -> None:
        """
        Resume a paused processing job.

        Args:
            db: Database session
            job_id: ID of the job to resume
        """
        job = db.query(Job).filter(
            Job.id == job_id,
            Job.status == 'paused'
        ).first()
        if job:
            job.status = 'queued'
            job.paused_at = None
            db.commit()

    @staticmethod
    def _calculate_sha256(file_path: str) -> str:
        """
        Calculate SHA256 hash of a file.

        Args:
            file_path: Path to the file

        Returns:
            Hex digest of SHA256 hash
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b''):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
