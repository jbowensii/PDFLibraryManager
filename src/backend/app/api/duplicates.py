"""
Duplicates API endpoints - list and resolve duplicate candidates.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..models import DuplicateCandidate, User
from ..schemas import DuplicateCandidateResponse, DuplicateResolveRequest
from ..database import get_db
from .auth import get_current_user

router = APIRouter()


@router.get('/', response_model=dict)
async def list_duplicates(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """
    List duplicate candidates. Only admins can view.

    Args:
        skip: Number of candidates to skip
        limit: Number of candidates to return
        db: Database session
        user: Current authenticated user

    Returns:
        dict: Total count and list of duplicate candidates

    Raises:
        HTTPException: If user is not admin
    """
    if user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view duplicate candidates"
        )

    total = db.query(DuplicateCandidate).count()
    candidates = db.query(DuplicateCandidate).offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [DuplicateCandidateResponse.from_orm(c) for c in candidates]
    }


@router.get('/{candidate_id}', response_model=DuplicateCandidateResponse)
async def get_duplicate_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DuplicateCandidateResponse:
    """
    Get a specific duplicate candidate. Only admins can view.

    Args:
        candidate_id: ID of the candidate
        db: Database session
        user: Current authenticated user

    Returns:
        DuplicateCandidateResponse: The candidate details

    Raises:
        HTTPException: If user is not admin or candidate not found
    """
    if user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view duplicate candidates"
        )

    candidate = db.query(DuplicateCandidate).filter(
        DuplicateCandidate.id == candidate_id
    ).first()

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate {candidate_id} not found"
        )

    return DuplicateCandidateResponse.from_orm(candidate)


@router.post('/{candidate_id}/resolve')
async def resolve_duplicate(
    candidate_id: int,
    request: DuplicateResolveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """
    Resolve a duplicate candidate by choosing which book to keep.

    Args:
        candidate_id: ID of the candidate
        request: Resolution request with keep_book_id
        db: Database session
        user: Current authenticated user

    Returns:
        dict: Resolution status

    Raises:
        HTTPException: If user is not admin, candidate not found, or invalid choice
    """
    if user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can resolve duplicates"
        )

    candidate = db.query(DuplicateCandidate).filter(
        DuplicateCandidate.id == candidate_id
    ).first()

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate {candidate_id} not found"
        )

    # Validate that keep_book_id is one of the two books
    if request.keep_book_id not in [candidate.book_id_1, candidate.book_id_2]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="keep_book_id must be one of the two candidate books"
        )

    # Determine which book to delete
    if request.keep_book_id == candidate.book_id_1:
        status_value = 'resolved_keep_1'
        delete_id = candidate.book_id_2
    else:
        status_value = 'resolved_keep_2'
        delete_id = candidate.book_id_1

    # Update candidate status
    candidate.status = status_value
    candidate.user_decision_by = user.id
    candidate.resolved_at = __import__('datetime').datetime.utcnow()

    db.commit()

    return {
        "status": "resolved",
        "candidate_id": candidate_id,
        "resolution": status_value,
        "kept_book_id": request.keep_book_id
    }
