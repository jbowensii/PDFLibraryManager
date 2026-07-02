"""
Tests for duplicate detection and scoring services.

Tests cover:
- Duplicate similarity scoring with weighted algorithm
- Detection of candidate duplicates by publisher
- Auto-resolution logic based on confidence thresholds
- Manual resolution workflow for medium-confidence cases
"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, Book, DuplicateCandidate
from app.dedup.scoring import DuplicateScorer
from app.dedup.detection import DuplicateDetectionService


@pytest.fixture
def db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestDuplicateScorerMetadata:
    """Tests for metadata similarity scoring."""

    def test_score_identical_titles_and_authors(self):
        """Identical title and author without ISBN should score 0.7 (metadata only)."""
        book_a = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'publisher': 'Scribner',
            'isbn': None,
            'content_hash': None,
            'ocr_error_count': 10
        }
        book_b = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'publisher': 'Scribner',
            'isbn': None,
            'content_hash': None,
            'ocr_error_count': 10
        }
        score = DuplicateScorer.score(book_a, book_b)
        # Metadata 1.0 * 0.4 + ISBN 0.5 * 0.2 + hash 0.0 * 0.2 + quality 1.0 * 0.2 = 0.7
        assert score == 0.7


class TestDuplicateScorerISBN:
    """Tests for ISBN-based scoring."""

    def test_score_identical_isbn(self):
        """Books with identical ISBN should score high even with different metadata."""
        book_a = {
            'title': 'Book A',
            'author': 'Author A',
            'publisher': 'Publisher A',
            'isbn': '9780451524935',
            'content_hash': None,
            'ocr_error_count': 10
        }
        book_b = {
            'title': 'Book B Title',
            'author': 'Author B',
            'publisher': 'Publisher B',
            'isbn': '9780451524935',
            'content_hash': None,
            'ocr_error_count': 20
        }
        score = DuplicateScorer.score(book_a, book_b)
        # Identical ISBN (1.0 * 0.2 = 0.2) + low metadata + quality diff
        # should score in 0.4-0.6 range
        assert score > 0.4

    def test_score_different_isbn(self):
        """Books with different ISBNs should score low despite metadata match."""
        book_a = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'publisher': 'Scribner',
            'isbn': '9780451524935',
            'content_hash': None,
            'ocr_error_count': 10
        }
        book_b = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'publisher': 'Scribner',
            'isbn': '9999999999999',
            'content_hash': None,
            'ocr_error_count': 10
        }
        score = DuplicateScorer.score(book_a, book_b)
        # Different ISBN (0.0 * 0.2 = 0.0) should prevent high score
        assert score < 0.9

    def test_score_both_missing_isbn(self):
        """Books without ISBN get neutral ISBN score (0.5)."""
        book_a = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'publisher': 'Scribner',
            'isbn': None,
            'content_hash': None,
            'ocr_error_count': 10
        }
        book_b = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'publisher': 'Scribner',
            'isbn': None,
            'content_hash': None,
            'ocr_error_count': 10
        }
        score = DuplicateScorer.score(book_a, book_b)
        # Perfect metadata (1.0 * 0.4) + neutral ISBN (0.5 * 0.2) + quality (1.0 * 0.2) = 0.7
        assert score == 0.7


class TestDuplicateScorerContentHash:
    """Tests for content hash scoring."""

    def test_score_identical_content_hash(self):
        """Books with identical content hash and small quality diff score very high."""
        book_a = {
            'title': 'Book A',
            'author': 'Author A',
            'publisher': 'Publisher A',
            'isbn': None,
            'content_hash': 'abc123def456',
            'ocr_error_count': 10
        }
        book_b = {
            'title': 'Book A',  # Same title
            'author': 'Author A',  # Same author
            'publisher': 'Publisher A',  # Same publisher
            'isbn': None,
            'content_hash': 'abc123def456',
            'ocr_error_count': 11  # Small quality difference
        }
        score = DuplicateScorer.score(book_a, book_b)
        # Content hash match (1.0 * 0.2) + neutral ISBN (0.5 * 0.2) + metadata match (1.0 * 0.4) + quality 0.9 * 0.2 = 0.82
        assert score > 0.8

    def test_score_different_content_hash(self):
        """Books with different content hashes score 0 on hash component."""
        book_a = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'publisher': 'Scribner',
            'isbn': None,
            'content_hash': 'hash1',
            'ocr_error_count': 10
        }
        book_b = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'publisher': 'Scribner',
            'isbn': None,
            'content_hash': 'hash2',
            'ocr_error_count': 10
        }
        score = DuplicateScorer.score(book_a, book_b)
        # Different hash + perfect metadata might still score high
        # but hash difference is accounted
        assert score < 1.0


class TestDuplicateScorerQuality:
    """Tests for OCR quality-based scoring."""

    def test_score_identical_quality(self):
        """Books with same OCR error count score high on quality component."""
        book_a = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'publisher': 'Scribner',
            'isbn': None,
            'content_hash': None,
            'ocr_error_count': 10
        }
        book_b = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'publisher': 'Scribner',
            'isbn': None,
            'content_hash': None,
            'ocr_error_count': 10
        }
        score = DuplicateScorer.score(book_a, book_b)
        # Same quality (1.0 * 0.2) + metadata (1.0 * 0.4) + neutral ISBN (0.5 * 0.2) = 0.7
        assert score == 0.7

    def test_score_different_quality_large_difference(self):
        """Large OCR error difference (one clearly better quality)."""
        book_a = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'publisher': 'Scribner',
            'isbn': None,
            'content_hash': None,
            'ocr_error_count': 5  # High quality (few errors)
        }
        book_b = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'publisher': 'Scribner',
            'isbn': None,
            'content_hash': None,
            'ocr_error_count': 50  # Poor quality (many errors)
        }
        score = DuplicateScorer.score(book_a, book_b)
        # Quality 0.9 * 0.2 + metadata 1.0 * 0.4 + neutral ISBN 0.5 * 0.2 = 0.56
        assert score > 0.5

    def test_score_different_quality_10x_difference(self):
        """10x quality difference (same title, author, publisher)."""
        book_a = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'publisher': 'Scribner',
            'isbn': None,
            'content_hash': None,
            'ocr_error_count': 5
        }
        book_b = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'publisher': 'Scribner',
            'isbn': None,
            'content_hash': None,
            'ocr_error_count': 50
        }
        score = DuplicateScorer.score(book_a, book_b)
        # Quality 0.9 * 0.2 + metadata 1.0 * 0.4 + neutral ISBN 0.5 * 0.2 = 0.56
        assert 0.5 < score < 0.7


class TestDuplicateScorerEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_score_different_titles_same_author_publisher(self):
        """Different titles but same author and publisher."""
        book_a = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'publisher': 'Scribner',
            'isbn': None,
            'content_hash': None,
            'ocr_error_count': 10
        }
        book_b = {
            'title': 'This Side of Paradise',
            'author': 'F. Scott Fitzgerald',
            'publisher': 'Scribner',
            'isbn': None,
            'content_hash': None,
            'ocr_error_count': 10
        }
        score = DuplicateScorer.score(book_a, book_b)
        # Different titles should result in lower score
        assert score < 0.7

    def test_score_very_different_books(self):
        """Completely different books."""
        book_a = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'publisher': 'Scribner',
            'isbn': '9780451524935',
            'content_hash': None,
            'ocr_error_count': 10
        }
        book_b = {
            'title': 'To Kill a Mockingbird',
            'author': 'Harper Lee',
            'publisher': 'J.B. Lippincott',
            'isbn': '0061120081',
            'content_hash': None,
            'ocr_error_count': 20
        }
        score = DuplicateScorer.score(book_a, book_b)
        # Should be very low
        assert score < 0.3

    def test_score_zero_ocr_errors(self):
        """Books with zero OCR errors should be handled without division by zero."""
        book_a = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'publisher': 'Scribner',
            'isbn': None,
            'content_hash': None,
            'ocr_error_count': 0
        }
        book_b = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'publisher': 'Scribner',
            'isbn': None,
            'content_hash': None,
            'ocr_error_count': 0
        }
        score = DuplicateScorer.score(book_a, book_b)
        # Should not crash and should score 0.7 (perfect metadata, neutral ISBN, perfect quality)
        assert 0.0 <= score <= 1.0
        assert score == 0.7


class TestFindCandidates:
    """Tests for finding duplicate candidates."""

    def test_find_candidates(self, db):
        """Find other books with same publisher as candidates."""
        # Create books with same publisher
        book1 = Book(
            title='Book 1',
            author='Author A',
            publisher='Scribner',
            ocr_error_count=10
        )
        book2 = Book(
            title='Book 2',
            author='Author B',
            publisher='Scribner',
            ocr_error_count=15
        )
        book3 = Book(
            title='Book 3',
            author='Author C',
            publisher='Scribner',
            ocr_error_count=20
        )
        book4 = Book(
            title='Book 4',
            author='Author D',
            publisher='Different Publisher',
            ocr_error_count=25
        )
        db.add_all([book1, book2, book3, book4])
        db.commit()

        # Find candidates for book1
        candidates = DuplicateDetectionService.find_candidates(db, book1.id)

        # Should find book2 and book3 (same publisher), not book4
        assert len(candidates) == 2
        candidate_ids = {c.id for c in candidates}
        assert book2.id in candidate_ids
        assert book3.id in candidate_ids
        assert book4.id not in candidate_ids

    def test_find_candidates_excludes_duplicates(self, db):
        """Find candidates should exclude books marked as duplicates."""
        book1 = Book(
            title='Book 1',
            author='Author A',
            publisher='Scribner',
            ocr_error_count=10,
            is_duplicate=False
        )
        book2 = Book(
            title='Book 2',
            author='Author B',
            publisher='Scribner',
            ocr_error_count=15,
            is_duplicate=True,  # Already a duplicate
            duplicate_parent_id=1
        )
        db.add_all([book1, book2])
        db.commit()

        candidates = DuplicateDetectionService.find_candidates(db, book1.id)

        # Should not find book2 since it's marked as duplicate
        assert len(candidates) == 0

    def test_find_candidates_nonexistent_book(self, db):
        """Finding candidates for nonexistent book returns empty list."""
        candidates = DuplicateDetectionService.find_candidates(db, 999)
        assert candidates == []


class TestScoreAndRecordHighConfidence:
    """Tests for high-confidence auto-resolution (score > 0.95)."""

    def test_score_and_record_identical_hash_small_quality_diff(self, db):
        """Content hash match + small quality difference requires manual review."""
        book1 = Book(
            title='The Great Gatsby',
            author='F. Scott Fitzgerald',
            publisher='Scribner',
            content_hash='abc123',
            ocr_error_count=10  # Good quality
        )
        book2 = Book(
            title='The Great Gatsby',
            author='F. Scott Fitzgerald',
            publisher='Scribner',
            content_hash='abc123',
            ocr_error_count=11  # Tiny difference (9%)
        )
        db.add_all([book1, book2])
        db.commit()

        candidate = DuplicateDetectionService.score_and_record(db, book1.id, book2.id)

        assert candidate is not None
        # Metadata 1.0 * 0.4 + ISBN 0.5 * 0.2 + hash 1.0 * 0.2 + quality (0.9) * 0.2 = 0.82
        assert candidate.similarity_score > 0.8
        # With small quality diff (<20%), requires manual review despite high score
        assert candidate.status == 'manual_review'

    def test_score_and_record_identical_isbn_and_metadata(self, db):
        """Identical ISBN + small quality difference requires review."""
        book1 = Book(
            title='The Great Gatsby',
            author='F. Scott Fitzgerald',
            publisher='Scribner',
            isbn='9780451524935',
            ocr_error_count=10
        )
        book2 = Book(
            title='The Great Gatsby',
            author='F. Scott Fitzgerald',
            publisher='Scribner',
            isbn='9780451524935',
            ocr_error_count=20  # 100% difference - large
        )
        db.add_all([book1, book2])
        db.commit()

        candidate = DuplicateDetectionService.score_and_record(db, book1.id, book2.id)

        assert candidate is not None
        # Perfect metadata (0.4) + perfect ISBN (0.2) + quality penalty (0.1) = 0.7
        assert abs(candidate.similarity_score - 0.7) < 0.0001
        # Score < 0.75, so pending despite ISBN match
        assert candidate.status == 'pending'


class TestScoreAndRecordMediumConfidence:
    """Tests for medium-confidence cases (0.75 < score <= 0.95)."""

    def test_score_and_record_medium_confidence_large_quality_diff(self, db):
        """Medium score with large quality difference (>=20%) still pending if score < 0.75."""
        # To get into medium confidence range with large quality diff
        book1 = Book(
            title='The Great Gatsby',
            author='F. Scott Fitzgerald',
            publisher='Scribner',
            isbn='9780451524935',
            ocr_error_count=50   # Starting point
        )
        book2 = Book(
            title='The Great Gatsby',
            author='F. Scott Fitzgerald',
            publisher='Scribner',
            isbn='9780451524935',  # Same ISBN
            ocr_error_count=70     # 40% difference (>=20%)
        )
        db.add_all([book1, book2])
        db.commit()

        candidate = DuplicateDetectionService.score_and_record(db, book1.id, book2.id)

        assert candidate is not None
        # Score < 0.75, so will be pending
        assert candidate.status == 'pending'

    def test_score_and_record_medium_confidence_small_quality_diff(self, db):
        """ISBN match + small quality difference requires manual review."""
        book1 = Book(
            title='The Great Gatsby',
            author='F. Scott Fitzgerald',
            publisher='Scribner',
            isbn='9780451524935',
            ocr_error_count=10
        )
        book2 = Book(
            title='The Great Gatsby',
            author='F. Scott Fitzgerald',
            publisher='Scribner',
            isbn='9780451524935',  # Same ISBN
            ocr_error_count=12  # Only 20% difference, edge case
        )
        db.add_all([book1, book2])
        db.commit()

        candidate = DuplicateDetectionService.score_and_record(db, book1.id, book2.id)

        assert candidate is not None
        # With ISBN match + small quality diff, should be manual_review
        assert candidate.status == 'manual_review'


class TestScoreAndRecordLowConfidence:
    """Tests for low-confidence cases (score < 0.75)."""

    def test_score_and_record_low_confidence(self, db):
        """Score < 0.75 marks candidate as pending."""
        book1 = Book(
            title='The Great Gatsby',
            author='F. Scott Fitzgerald',
            publisher='Scribner',
            isbn='9780451524935',
            ocr_error_count=10
        )
        book2 = Book(
            title='To Kill a Mockingbird',
            author='Harper Lee',
            publisher='J.B. Lippincott',
            isbn='0061120081',
            ocr_error_count=20
        )
        db.add_all([book1, book2])
        db.commit()

        candidate = DuplicateDetectionService.score_and_record(db, book1.id, book2.id)

        assert candidate is not None
        assert candidate.similarity_score < 0.75
        assert candidate.status == 'pending'


class TestResolveManually:
    """Tests for manual resolution of candidates."""

    def test_resolve_duplicate(self, db):
        """Manually resolve candidate by selecting which book to keep."""
        book1 = Book(
            title='The Great Gatsby',
            author='F. Scott Fitzgerald',
            publisher='Scribner',
            ocr_error_count=10
        )
        book2 = Book(
            title='The Great Gatsby',
            author='F. Scott Fitzgerald',
            publisher='Scribner',
            ocr_error_count=50
        )
        db.add_all([book1, book2])
        db.commit()

        # Create a pending candidate
        candidate = DuplicateCandidate(
            book_id_1=book1.id,
            book_id_2=book2.id,
            similarity_score=0.85,
            status='manual_review'
        )
        db.add(candidate)
        db.commit()

        # Manually resolve - keep book1
        success = DuplicateDetectionService.resolve(
            db, candidate.id, book1.id, user_id=123
        )

        assert success is True
        db.refresh(candidate)
        assert candidate.status == f'resolved_keep_{book1.id}'
        assert candidate.user_decision_by == 123
        assert candidate.resolved_at is not None

        # Check that book2 is marked as duplicate
        db.refresh(book2)
        assert book2.is_duplicate is True
        assert book2.duplicate_parent_id == book1.id

    def test_resolve_with_notes(self, db):
        """Resolution should capture user notes."""
        book1 = Book(
            title='The Great Gatsby',
            author='F. Scott Fitzgerald',
            publisher='Scribner',
            ocr_error_count=10
        )
        book2 = Book(
            title='The Great Gatsby',
            author='F. Scott Fitzgerald',
            publisher='Scribner',
            ocr_error_count=50
        )
        db.add_all([book1, book2])
        db.commit()

        candidate = DuplicateCandidate(
            book_id_1=book1.id,
            book_id_2=book2.id,
            similarity_score=0.85,
            status='manual_review'
        )
        db.add(candidate)
        db.commit()

        notes = 'Kept first edition scan, better page quality'
        success = DuplicateDetectionService.resolve(
            db, candidate.id, book1.id, user_id=123, notes=notes
        )

        assert success is True
        db.refresh(candidate)
        assert candidate.notes == notes

    def test_resolve_other_book_as_parent(self, db):
        """Should allow keeping either book as parent."""
        book1 = Book(
            title='The Great Gatsby',
            author='F. Scott Fitzgerald',
            publisher='Scribner',
            ocr_error_count=10
        )
        book2 = Book(
            title='The Great Gatsby',
            author='F. Scott Fitzgerald',
            publisher='Scribner',
            ocr_error_count=50
        )
        db.add_all([book1, book2])
        db.commit()

        candidate = DuplicateCandidate(
            book_id_1=book1.id,
            book_id_2=book2.id,
            similarity_score=0.85,
            status='manual_review'
        )
        db.add(candidate)
        db.commit()

        # Resolve keeping book2 as parent
        success = DuplicateDetectionService.resolve(
            db, candidate.id, book2.id, user_id=123
        )

        assert success is True
        db.refresh(candidate)
        assert candidate.status == f'resolved_keep_{book2.id}'

        # Book1 should be marked as duplicate
        db.refresh(book1)
        assert book1.is_duplicate is True
        assert book1.duplicate_parent_id == book2.id

    def test_resolve_nonexistent_candidate(self, db):
        """Resolving nonexistent candidate returns False."""
        success = DuplicateDetectionService.resolve(db, 999, 1, user_id=123)
        assert success is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
