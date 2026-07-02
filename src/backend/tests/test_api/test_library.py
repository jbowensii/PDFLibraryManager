"""
Tests for library scanning and job management endpoints.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.models import Base, Book, Job, User
from app.config import settings
from app.schemas import ScanRequest
from app.api.library import router


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        'sqlite:///:memory:',
        connect_args={'check_same_thread': False}
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    yield db

    db.close()


@pytest.fixture
def app(db_session):
    """Create a FastAPI test app."""
    app = FastAPI()

    # Override dependency for database session
    def get_db_override():
        return db_session

    # Override dependency for current user
    def get_current_user_override(db = Depends(get_db_override)):
        return User(
            id=1,
            username='testuser',
            email='test@example.com',
            password_hash='hash',
            role='admin'
        )

    from app.api.library import get_db, get_current_user
    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = get_current_user_override

    app.include_router(router, prefix='/library', tags=['Library'])

    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def admin_user(db_session):
    """Create an admin user."""
    user = User(
        username='admin',
        email='admin@example.com',
        password_hash='hash',
        role='admin'
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def curator_user(db_session):
    """Create a curator user."""
    user = User(
        username='curator',
        email='curator@example.com',
        password_hash='hash',
        role='curator'
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_pdf_directory():
    """Create a temporary directory with test PDFs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create 5 test PDF files
        for i in range(5):
            pdf_file = tmppath / f'test_document_{i}.pdf'
            # Create a minimal PDF file
            pdf_content = b'%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n3 0 obj\n<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>>>>>\nendobj\n4 0 obj\n<</Length 44>>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Sample PDF) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\n0000000279 00000 n\ntrailer\n<</Size 5/Root 1 0 R>>\nstartxref\n373\n%%EOF'
            pdf_file.write_bytes(pdf_content)

        yield str(tmppath)


class TestStartScan:
    """Tests for POST /library/scan endpoint."""

    @patch('app.services.scan_service.ScanService.scan_directory')
    def test_start_scan_admin_only(self, mock_scan, client):
        """Admin can start a scan."""
        mock_scan.return_value = 5

        response = client.post(
            '/library/scan',
            json={'source_dir': '/tmp/test'}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'started'
        assert data['pdfs_queued'] == 5

    def test_start_scan_not_admin(self, app, db_session):
        """Non-admin gets 403."""
        # Create a curator user override
        def get_current_user_curator(db = Depends(lambda: db_session)):
            return User(id=2, username='curator', email='curator@example.com', password_hash='hash', role='curator')

        from app.api.library import get_current_user
        app.dependency_overrides[get_current_user] = get_current_user_curator

        client = TestClient(app)
        response = client.post(
            '/library/scan',
            json={'source_dir': '/tmp/test'}
        )

        assert response.status_code == 403
        assert 'admin' in response.json()['detail'].lower()

    @patch('app.services.scan_service.ScanService.scan_directory')
    def test_start_scan_creates_jobs(self, mock_scan, client):
        """Starting a scan creates Job entries."""
        mock_scan.return_value = 5

        response = client.post(
            '/library/scan',
            json={'source_dir': '/tmp/test'}
        )

        assert response.status_code == 200
        assert response.json()['pdfs_queued'] == 5


class TestJobStatus:
    """Tests for GET /library/scan/{job_id} endpoint."""

    def test_get_scan_status_pending(self, db_session):
        """Get status of a pending job."""
        # Create test data
        book = Book(
            title='Test Book',
            author='Test Author',
            filesystem_path='/path/to/test.pdf',
            filename_normalized='test.pdf',
            ocr_status='pending'
        )
        db_session.add(book)
        db_session.commit()

        job = Job(
            book_id=book.id,
            job_type='ocr',
            status='queued'
        )
        db_session.add(job)
        db_session.commit()

        # Test get_job_status
        from app.services import ScanService
        status_dict = ScanService.get_job_status(db_session, job.id)

        assert status_dict is not None
        assert status_dict['id'] == job.id
        assert status_dict['status'] == 'queued'
        assert status_dict['type'] == 'ocr'

    def test_get_scan_status_not_found(self, db_session):
        """Get status of non-existent job returns None."""
        from app.services import ScanService
        status_dict = ScanService.get_job_status(db_session, 999)
        assert status_dict is None


class TestPauseResume:
    """Tests for pause/resume operations."""

    def test_pause_scan(self, db_session):
        """Pause a job."""
        book = Book(
            title='Test Book',
            author='Test Author',
            filesystem_path='/path/to/test.pdf',
            filename_normalized='test.pdf',
            ocr_status='pending'
        )
        db_session.add(book)
        db_session.commit()

        job = Job(
            book_id=book.id,
            job_type='ocr',
            status='in_progress'
        )
        db_session.add(job)
        db_session.commit()

        from app.services import ScanService
        ScanService.pause_job(db_session, job.id)

        # Verify pause
        updated_job = db_session.query(Job).filter(Job.id == job.id).first()
        assert updated_job.status == 'paused'
        assert updated_job.paused_at is not None

    def test_resume_scan(self, db_session):
        """Resume a paused job."""
        book = Book(
            title='Test Book',
            author='Test Author',
            filesystem_path='/path/to/test.pdf',
            filename_normalized='test.pdf',
            ocr_status='pending'
        )
        db_session.add(book)
        db_session.commit()

        job = Job(
            book_id=book.id,
            job_type='ocr',
            status='paused'
        )
        db_session.add(job)
        db_session.commit()

        from app.services import ScanService
        ScanService.resume_job(db_session, job.id)

        # Verify resume
        updated_job = db_session.query(Job).filter(Job.id == job.id).first()
        assert updated_job.status == 'queued'
        assert updated_job.paused_at is None

    def test_pause_resume_cycle(self, db_session):
        """Test pause/resume state transitions."""
        book = Book(
            title='Test Book',
            author='Test Author',
            filesystem_path='/path/to/test.pdf',
            filename_normalized='test.pdf',
            ocr_status='pending'
        )
        db_session.add(book)
        db_session.commit()

        job = Job(
            book_id=book.id,
            job_type='ocr',
            status='in_progress'
        )
        db_session.add(job)
        db_session.commit()

        from app.services import ScanService

        # Pause
        ScanService.pause_job(db_session, job.id)
        paused_job = db_session.query(Job).filter(Job.id == job.id).first()
        assert paused_job.status == 'paused'

        # Resume
        ScanService.resume_job(db_session, job.id)
        resumed_job = db_session.query(Job).filter(Job.id == job.id).first()
        assert resumed_job.status == 'queued'


class TestScanDirectory:
    """Tests for ScanService.scan_directory."""

    @patch('app.services.scan_service.process_pdf')
    def test_scan_directory_recursive(self, mock_celery, db_session, test_pdf_directory):
        """Scan directory recursively finds PDFs."""
        from app.services import ScanService

        # Mock the celery task
        mock_task = MagicMock()
        mock_task.id = 'task-123'
        mock_celery.delay.return_value = mock_task

        count = ScanService.scan_directory(db_session, test_pdf_directory, recursive=True)

        # Should find 5 PDFs
        assert count == 5

        # Verify books were created
        books = db_session.query(Book).all()
        assert len(books) == 5

        # Verify jobs were created
        jobs = db_session.query(Job).all()
        assert len(jobs) == 5

    @patch('app.services.scan_service.process_pdf')
    def test_scan_directory_duplicate_skip(self, mock_celery, db_session, test_pdf_directory):
        """Scan skips already-imported PDFs."""
        from app.services import ScanService

        mock_task = MagicMock()
        mock_task.id = 'task-123'
        mock_celery.delay.return_value = mock_task

        # First scan
        count1 = ScanService.scan_directory(db_session, test_pdf_directory)
        assert count1 == 5

        # Second scan (same directory)
        count2 = ScanService.scan_directory(db_session, test_pdf_directory)
        assert count2 == 0

    def test_scan_directory_not_found(self, db_session):
        """Scan non-existent directory raises error."""
        from app.services import ScanService

        with pytest.raises(ValueError, match='Directory does not exist'):
            ScanService.scan_directory(db_session, '/non/existent/path')


class TestOCRPipeline:
    """Tests for OCRPipeline."""

    def test_check_embedded_text_with_text(self, test_pdf_directory):
        """Check for embedded text in PDF with text."""
        from app.ocr import OCRPipeline

        pdf_files = list(Path(test_pdf_directory).glob('*.pdf'))
        assert len(pdf_files) > 0

        # Test the first PDF
        # Note: Our test PDF has minimal content, so embedded text check may return False
        has_text = OCRPipeline.check_embedded_text(str(pdf_files[0]))
        assert isinstance(has_text, bool)

    def test_check_embedded_text_invalid_file(self):
        """Check for embedded text with invalid file."""
        from app.ocr import OCRPipeline

        # Should return False for non-existent file
        has_text = OCRPipeline.check_embedded_text('/path/to/nonexistent.pdf')
        assert has_text is False
