"""
Duplicate detection and resolution service.

Provides automated detection of duplicate books, scoring, and resolution
workflow with decision tree for auto-deletion and user review.

Decision thresholds:
- score > 0.95: Auto-delete lower quality copy
- 0.75 < score <= 0.95:
  - >= 20% OCR error difference: Auto-delete lower quality copy
  - < 20% OCR error difference: Manual review required
- score <= 0.75: Pending (low confidence, user decision only)
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from .scoring import DuplicateScorer


class DuplicateDetectionService:
    """Service for detecting, scoring, and resolving duplicate books."""

    @staticmethod
    def find_candidates(db: Session, book_id: int) -> List:
        """
        Find potential duplicate candidates for a given book.

        Uses publisher as a broad search criterion to identify books that
        are likely to be related (same work, different scans).

        Args:
            db: SQLAlchemy database session
            book_id: ID of the book to find duplicates for

        Returns:
            List of Book objects that share the same publisher and are
            not already marked as duplicates (is_duplicate=False)

        Note:
            This performs a broad search. The actual scoring/filtering
            happens in score_and_record().
        """
        # Import here to avoid circular dependency
        from ..models import Book

        # Get the book we're checking
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            return []

        # Find other books with same publisher, excluding duplicates
        candidates = db.query(Book).filter(
            Book.publisher == book.publisher,
            Book.is_duplicate == False,
            Book.id != book_id
        ).all()

        return candidates

    @staticmethod
    def score_and_record(db: Session, book_a_id: int, book_b_id: int) -> Optional:
        """
        Score two books for duplication and record the result.

        Calculates similarity score and applies decision tree to determine
        if the duplicate should be auto-resolved or marked for manual review.

        Decision tree:
        - score > 0.95: Auto-delete lower quality copy
        - 0.75 < score <= 0.95:
            - If error_diff >= 20%: Auto-delete lower quality copy
            - If error_diff < 20%: Mark for manual review
        - score <= 0.75: Mark as pending (low confidence)

        Args:
            db: SQLAlchemy database session
            book_a_id: ID of first book to compare
            book_b_id: ID of second book to compare

        Returns:
            DuplicateCandidate object with calculated score and status,
            or None if books don't exist

        Side effects:
            - Creates DuplicateCandidate record in database
            - For auto-resolved duplicates: marks loser book as
              is_duplicate=True, duplicate_parent_id=winner
            - Commits database transaction
        """
        # Import here to avoid circular dependency
        from ..models import Book, DuplicateCandidate

        # Fetch both books
        book_a = db.query(Book).filter(Book.id == book_a_id).first()
        book_b = db.query(Book).filter(Book.id == book_b_id).first()

        if not book_a or not book_b:
            return None

        # Convert books to dictionaries for scoring
        book_a_dict = {
            'title': book_a.title,
            'author': book_a.author,
            'publisher': book_a.publisher,
            'isbn': book_a.isbn,
            'content_hash': book_a.content_hash,
            'ocr_error_count': book_a.ocr_error_count
        }

        book_b_dict = {
            'title': book_b.title,
            'author': book_b.author,
            'publisher': book_b.publisher,
            'isbn': book_b.isbn,
            'content_hash': book_b.content_hash,
            'ocr_error_count': book_b.ocr_error_count
        }

        # Calculate score
        score = DuplicateScorer.score(book_a_dict, book_b_dict)

        # Apply decision tree
        status = 'pending'
        auto_delete_loser_id = None

        if score > 0.95:
            # High confidence - auto-delete lower quality copy
            if book_a.ocr_error_count <= book_b.ocr_error_count:
                status = f'resolved_keep_{book_a_id}'
                auto_delete_loser_id = book_b_id
            else:
                status = f'resolved_keep_{book_b_id}'
                auto_delete_loser_id = book_a_id

        elif score > 0.75:
            # Medium confidence - check quality difference
            error_diff = abs(book_a.ocr_error_count - book_b.ocr_error_count)
            max_errors = max(book_a.ocr_error_count, book_b.ocr_error_count, 1)
            error_diff_percent = (error_diff / max_errors) * 100

            if error_diff_percent >= 20:
                # Significant quality difference - auto-resolve
                if book_a.ocr_error_count <= book_b.ocr_error_count:
                    status = f'resolved_keep_{book_a_id}'
                    auto_delete_loser_id = book_b_id
                else:
                    status = f'resolved_keep_{book_b_id}'
                    auto_delete_loser_id = book_a_id
            else:
                # Minor quality difference - ask user
                status = 'manual_review'

        # Create candidate record
        candidate = DuplicateCandidate(
            book_id_1=book_a_id,
            book_id_2=book_b_id,
            similarity_score=score,
            status=status,
            user_decision_by=None,
            resolved_at=datetime.utcnow() if status.startswith('resolved') else None,
            notes=None
        )

        db.add(candidate)

        # If auto-resolved, mark the loser as duplicate
        if auto_delete_loser_id is not None:
            loser = db.query(Book).filter(Book.id == auto_delete_loser_id).first()
            winner_id = book_a_id if auto_delete_loser_id == book_b_id else book_b_id
            if loser:
                loser.is_duplicate = True
                loser.duplicate_parent_id = winner_id

        db.commit()
        return candidate

    @staticmethod
    def resolve(db: Session, candidate_id: int, keep_book_id: int,
                user_id: int, notes: Optional[str] = None) -> bool:
        """
        Manually resolve a duplicate candidate by selecting which copy to keep.

        Marks the losing book as a duplicate and updates the candidate status.

        Args:
            db: SQLAlchemy database session
            candidate_id: ID of the DuplicateCandidate to resolve
            keep_book_id: ID of the book to keep (the winner)
            user_id: ID of the user making the decision
            notes: Optional notes about the decision

        Returns:
            True if resolution successful, False if candidate not found

        Side effects:
            - Marks losing book: is_duplicate=True, duplicate_parent_id=keep_book_id
            - Updates candidate: status='resolved_keep_{keep_book_id}',
              user_decision_by=user_id, notes=notes, resolved_at=datetime.utcnow()
            - Commits database transaction
        """
        # Import here to avoid circular dependency
        from ..models import Book, DuplicateCandidate

        candidate = db.query(DuplicateCandidate).filter(
            DuplicateCandidate.id == candidate_id
        ).first()

        if not candidate:
            return False

        # Determine which book to delete
        delete_id = candidate.book_id_2 if candidate.book_id_1 == keep_book_id else candidate.book_id_1

        # Mark loser as duplicate
        loser = db.query(Book).filter(Book.id == delete_id).first()
        if loser:
            loser.is_duplicate = True
            loser.duplicate_parent_id = keep_book_id

        # Update candidate
        candidate.status = f'resolved_keep_{keep_book_id}'
        candidate.user_decision_by = user_id
        candidate.notes = notes
        candidate.resolved_at = datetime.utcnow()

        db.commit()
        return True
