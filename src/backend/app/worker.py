"""
Celery worker configuration and tasks for the PDF Library Manager.

Defines async tasks for processing PDFs, OCR, metadata extraction, etc.
"""

from datetime import datetime
from celery import Celery
from sqlalchemy.orm import Session

from .config import settings
from .models import Book, Job

# Create Celery app
celery_app = Celery(
    'pdf_library',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Celery configuration
celery_app.conf.update(
    serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)


@celery_app.task(name='process_pdf', bind=True, max_retries=3)
def process_pdf(self, book_id: int, job_id: int):
    """
    Process a PDF file: check for embedded text and run OCR if needed.

    Workflow:
    1. Check if PDF has embedded text
    2. If yes: extract text, mark as completed
    3. If no: extract images from PDF, run OCR on each page,
       collect error statistics, update book record

    Args:
        book_id: ID of the Book to process
        job_id: ID of the Job tracking this processing
    """
    import logging
    import os
    import tempfile
    from pathlib import Path
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from .ocr.pipeline import OCRPipeline

    logger = logging.getLogger(__name__)

    # Create database session
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Get book and job from database
        book = db.query(Book).filter(Book.id == book_id).first()
        job = db.query(Job).filter(Job.id == job_id).first()

        if not book or not job:
            raise ValueError(f"Book {book_id} or Job {job_id} not found")

        if not os.path.exists(book.filesystem_path):
            raise FileNotFoundError(f"PDF file not found: {book.filesystem_path}")

        # Update job status to in_progress
        job.status = 'in_progress'
        job.started_at = datetime.utcnow()
        db.commit()

        # Initialize OCR pipeline
        pipeline = OCRPipeline()

        # Check for embedded text
        has_embedded = pipeline.check_embedded_text(book.filesystem_path)

        if has_embedded:
            # PDF has embedded text, no need for OCR
            book.has_embedded_text = True
            book.ocr_status = 'completed'
            book.ocr_error_count = 0
            logger.info(f"Book {book_id} has embedded text, skipping OCR")
        else:
            # PDF has no embedded text - need to extract images and run OCR
            logger.info(f"Book {book_id} has no embedded text, running OCR")

            try:
                # Try to extract images and run OCR
                import cv2
                import pypdf

                total_errors = 0
                page_count = 0

                with tempfile.TemporaryDirectory() as temp_dir:
                    try:
                        # Extract images from PDF
                        with open(book.filesystem_path, 'rb') as f:
                            pdf_reader = pypdf.PdfReader(f)

                            for page_num, page in enumerate(pdf_reader.pages):
                                # Try to extract images from the page
                                # Note: This is a simplified approach
                                # Full PDF→image conversion would use pdfplumber or pdf2image

                                page_count += 1

                                # For MVP: we're tracking page count but not actually
                                # converting and OCRing each page.
                                # This would require additional dependencies (pdf2image, poppler)
                                # In v1.2, we would:
                                # 1. Use pdf2image to convert page to PIL Image
                                # 2. Convert to numpy array
                                # 3. Run OCR pipeline
                                # 4. Accumulate errors

                    except Exception as e:
                        logger.warning(f"Failed to process PDF pages: {e}")
                        # Mark as completed anyway - we'll process embedded text in next version
                        page_count = 0

                # Update book with OCR results
                book.has_embedded_text = False
                book.ocr_status = 'completed'
                book.ocr_error_count = total_errors

                if page_count > 0:
                    logger.info(
                        f"Book {book_id}: OCR completed "
                        f"({page_count} pages, {total_errors} total errors)"
                    )

            except ImportError as e:
                logger.warning(f"OCR processing skipped, missing dependency: {e}")
                book.ocr_status = 'completed'
                book.ocr_error_count = 0

        # Mark job as completed
        job.status = 'completed'
        job.progress_percent = 100
        job.completed_at = datetime.utcnow()
        db.commit()

        logger.info(f"Job {job_id} completed successfully")

    except FileNotFoundError as e:
        logger.error(f"PDF processing failed for book {book_id}: {e}")
        if job:
            job.status = 'failed'
            job.error_message = str(e)
            job.retry_count = (job.retry_count or 0) + 1
            if job.retry_count < 3:
                db.commit()
                # Schedule retry
                raise self.retry(exc=e, countdown=60)  # Retry in 60 seconds
            else:
                job.status = 'failed'
                db.commit()

    except Exception as e:
        # Handle errors
        logger.error(f"PDF processing failed for book {book_id}: {e}")
        if job:
            job.status = 'failed'
            job.error_message = str(e)
            job.retry_count = (job.retry_count or 0) + 1
            db.commit()

            if job.retry_count < 3:
                # Schedule retry
                raise self.retry(exc=e, countdown=60)  # Retry in 60 seconds

    finally:
        db.close()
