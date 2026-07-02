"""
Duplicate similarity scoring algorithm.

Provides DuplicateScorer for calculating similarity scores between books
to determine likelihood they are the same work scanned multiple times.

Scoring methodology:
- Metadata Score (40% weight): Fuzzy matching on title, author, publisher
- ISBN Score (20% weight): Exact ISBN match is strongest signal
- Content Hash Score (20% weight): File-level hash is definitive proof
- Quality Score (20% weight): OCR error count indicates scan quality
"""

from typing import Dict
from fuzzywuzzy import fuzz


class DuplicateScorer:
    """Service for calculating duplicate similarity scores between books."""

    @staticmethod
    def score(book_a: Dict, book_b: Dict) -> float:
        """
        Calculate duplicate similarity score between two books.

        Uses a weighted formula combining:
        - Metadata matching (title, author, publisher) - 40%
        - ISBN matching - 20%
        - Content hash matching - 20%
        - OCR quality comparison - 20%

        Args:
            book_a: First book dictionary with keys: title, author, publisher,
                   isbn (optional), content_hash (optional), ocr_error_count
            book_b: Second book dictionary with keys: title, author, publisher,
                   isbn (optional), content_hash (optional), ocr_error_count

        Returns:
            Similarity score from 0.0 to 1.0, where higher values indicate
            greater likelihood of being the same work. Scores > 0.95 suggest
            auto-deletion, 0.75-0.95 require quality analysis, < 0.75 need
            user review.
        """
        # Calculate metadata score (40% weight)
        metadata_score = DuplicateScorer._calculate_metadata_score(book_a, book_b)

        # Calculate ISBN score (20% weight)
        isbn_score = DuplicateScorer._calculate_isbn_score(book_a, book_b)

        # Calculate content hash score (20% weight)
        content_hash_score = DuplicateScorer._calculate_content_hash_score(book_a, book_b)

        # Calculate quality score (20% weight)
        quality_score = DuplicateScorer._calculate_quality_score(book_a, book_b)

        # Weighted overall score
        overall = (
            (metadata_score * 0.4) +
            (isbn_score * 0.2) +
            (content_hash_score * 0.2) +
            (quality_score * 0.2)
        )

        return overall

    @staticmethod
    def _calculate_metadata_score(book_a: Dict, book_b: Dict) -> float:
        """
        Calculate metadata similarity score.

        Combines fuzzy matching on title (50%), author (30%), and publisher (20%).

        Args:
            book_a: First book dictionary
            book_b: Second book dictionary

        Returns:
            Metadata score from 0.0 to 1.0
        """
        title_sim = fuzz.token_set_ratio(
            book_a.get('title', ''),
            book_b.get('title', '')
        ) / 100.0

        author_sim = fuzz.token_set_ratio(
            book_a.get('author', ''),
            book_b.get('author', '')
        ) / 100.0

        pub_sim = fuzz.token_set_ratio(
            book_a.get('publisher', ''),
            book_b.get('publisher', '')
        ) / 100.0

        metadata_score = (title_sim * 0.5) + (author_sim * 0.3) + (pub_sim * 0.2)
        return metadata_score

    @staticmethod
    def _calculate_isbn_score(book_a: Dict, book_b: Dict) -> float:
        """
        Calculate ISBN match score.

        ISBN is a unique identifier. If both have ISBNs:
        - Match: 1.0 (definitive same book)
        - Different: 0.0 (definitive different books)
        If one or both missing: uncertain signal

        Args:
            book_a: First book dictionary
            book_b: Second book dictionary

        Returns:
            ISBN score from 0.0 to 1.0
        """
        isbn_a = book_a.get('isbn')
        isbn_b = book_b.get('isbn')

        # Both have ISBNs
        if isbn_a and isbn_b:
            return 1.0 if isbn_a == isbn_b else 0.0

        # Neither have ISBNs - uncertain but slightly positive
        if not isbn_a and not isbn_b:
            return 0.5

        # Only one has ISBN - weak signal (don't know about the other)
        return 0.2

    @staticmethod
    def _calculate_content_hash_score(book_a: Dict, book_b: Dict) -> float:
        """
        Calculate content hash match score.

        File-level hash is the strongest signal of identical content.
        If either book lacks a hash, score is 0 (not applicable).

        Args:
            book_a: First book dictionary
            book_b: Second book dictionary

        Returns:
            Content hash score from 0.0 to 1.0
        """
        hash_a = book_a.get('content_hash')
        hash_b = book_b.get('content_hash')

        # Both have hashes
        if hash_a and hash_b:
            return 1.0 if hash_a == hash_b else 0.0

        # Either missing - not applicable
        return 0.0

    @staticmethod
    def _calculate_quality_score(book_a: Dict, book_b: Dict) -> float:
        """
        Calculate quality difference score.

        OCR error count indicates scan quality. If one copy has significantly
        better OCR (fewer errors), it's the better copy to keep.

        Score is based on error difference ratio. Books with similar error
        counts score high (both equally poor/good). Books with different
        error counts score lower (one significantly better).

        Args:
            book_a: First book dictionary with 'ocr_error_count' key
            book_b: Second book dictionary with 'ocr_error_count' key

        Returns:
            Quality score from 0.0 to 1.0
        """
        errors_a = book_a.get('ocr_error_count', 0)
        errors_b = book_b.get('ocr_error_count', 0)

        max_errors = max(errors_a, errors_b, 1)  # Avoid division by zero
        error_diff = abs(errors_a - errors_b)

        quality_score = 1.0 - (error_diff / max_errors)

        # Clamp to 0.0 minimum
        return max(0.0, quality_score)
