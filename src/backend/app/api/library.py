"""
Library scanning and job management API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..config import settings
from ..models import User
from ..schemas import ScanRequest, ScanResponse, JobResponse
from ..services import ScanService
from ..database import get_db
from ..api.auth import get_current_user

router = APIRouter()


@router.post('/scan', response_model=ScanResponse)
async def start_scan(
    request: ScanRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ScanResponse:
    """
    Start a library scan to discover and queue PDFs for processing.

    Only admins can trigger scans.
    """
    if user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only admins can trigger library scans'
        )

    scan_dir = request.source_dir or settings.LIBRARY_ROOT_PATH

    try:
        count = ScanService.scan_directory(db, scan_dir)
        return ScanResponse(status='started', pdfs_queued=count)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get('/scan/{job_id}', response_model=JobResponse)
async def get_scan_status(
    job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JobResponse:
    """
    Get the status of a library scan job.
    """
    status_dict = ScanService.get_job_status(db, job_id)

    if not status_dict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Job {job_id} not found'
        )

    return JobResponse(**status_dict)


@router.post('/scan/{job_id}/pause')
async def pause_scan(
    job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """
    Pause a library scan job.

    Only admins can pause jobs.
    """
    if user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only admins can pause jobs'
        )

    ScanService.pause_job(db, job_id)
    return {'status': 'paused'}


@router.post('/scan/{job_id}/resume')
async def resume_scan(
    job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """
    Resume a paused library scan job.

    Only admins can resume jobs.
    """
    if user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only admins can resume jobs'
        )

    ScanService.resume_job(db, job_id)
    return {'status': 'resumed'}
