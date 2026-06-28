"""Celery worker configuration and task definitions."""

import logging
from celery import Celery, signals
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize Celery app
celery_app = Celery(
    "pdf_library_manager",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes hard limit
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)


@signals.worker_ready.connect
def worker_ready(**kwargs):
    """Log when the Celery worker is ready."""
    logger.info("Celery worker is ready to accept tasks")


@signals.worker_shutdown.connect
def worker_shutdown(**kwargs):
    """Log when the Celery worker is shutting down."""
    logger.info("Celery worker is shutting down")


@celery_app.task(name="scan_library", bind=True)
def scan_library(self):
    """Scan library for new PDFs and initiate processing."""
    logger.info("Starting library scan task")
    # Task implementation will be added based on specific requirements
    return {"status": "scan_completed", "task_id": self.request.id}


@celery_app.task(name="process_pdf", bind=True)
def process_pdf(self, book_id: int):
    """Process a single PDF for OCR and metadata extraction."""
    logger.info(f"Processing PDF for book_id={book_id}")
    # Task implementation will be added based on specific requirements
    return {"book_id": book_id, "status": "processed", "task_id": self.request.id}


@celery_app.task(name="extract_metadata", bind=True)
def extract_metadata(self, book_id: int):
    """Extract metadata from a PDF."""
    logger.info(f"Extracting metadata for book_id={book_id}")
    # Task implementation will be added based on specific requirements
    return {"book_id": book_id, "status": "metadata_extracted", "task_id": self.request.id}


@celery_app.task(name="ocr_text", bind=True)
def ocr_text(self, book_id: int):
    """Perform OCR on a PDF to extract text."""
    logger.info(f"Running OCR for book_id={book_id}")
    # Task implementation will be added based on specific requirements
    return {"book_id": book_id, "status": "ocr_completed", "task_id": self.request.id}


@celery_app.task(name="find_duplicates", bind=True)
def find_duplicates(self, book_id: int = None):
    """Find duplicate PDFs in the library."""
    logger.info(f"Finding duplicates for book_id={book_id if book_id else 'all'}")
    # Task implementation will be added based on specific requirements
    return {"status": "duplicates_found", "task_id": self.request.id}
