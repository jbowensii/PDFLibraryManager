"""
Fuzzy string matching service for metadata matching.

Provides fuzzy matching capabilities to determine similarity between
book metadata extracted from PDFs and API results. Uses token_set_ratio
for robust partial matching that handles word order differences.
"""

from typing import Dict
from fuzzywuzzy import fuzz


class MetadataMatchingService:
    """Service for fuzzy matching metadata fields to determine confidence scores."""

    @staticmethod
    def title_similarity(title1: str, title2: str) -> float:
        """
        Calculate similarity between two book titles.

        Uses token_set_ratio from fuzzywuzzy to handle partial matches
        and word order differences robustly.

        Args:
            title1: First title to compare
            title2: Second title to compare

        Returns:
            Similarity score from 0.0 to 1.0, where 1.0 is exact match
        """
        return fuzz.token_set_ratio(title1, title2) / 100.0

    @staticmethod
    def author_similarity(author1: str, author2: str) -> float:
        """
        Calculate similarity between two author names.

        Uses token_set_ratio for robust handling of name variations,
        middle names, and different orderings.

        Args:
            author1: First author name to compare
            author2: Second author name to compare

        Returns:
            Similarity score from 0.0 to 1.0, where 1.0 is exact match
        """
        return fuzz.token_set_ratio(author1, author2) / 100.0

    @staticmethod
    def publisher_similarity(pub1: str, pub2: str) -> float:
        """
        Calculate similarity between two publisher names.

        Uses token_set_ratio for handling publisher name variations
        and abbreviated names.

        Args:
            pub1: First publisher name to compare
            pub2: Second publisher name to compare

        Returns:
            Similarity score from 0.0 to 1.0, where 1.0 is exact match
        """
        return fuzz.token_set_ratio(pub1, pub2) / 100.0

    @staticmethod
    def calculate_confidence(extracted: Dict, api_result: Dict) -> float:
        """
        Calculate overall confidence score for a metadata match.

        Combines title and author similarity with weighted formula:
        - Title: 60% weight
        - Author: 40% weight

        Decision rule:
        - >= 0.9: auto-apply (high confidence, no user confirmation needed)
        - < 0.9: ask user to confirm (moderate to low confidence)

        Args:
            extracted: Dictionary with keys 'title' and 'author' from PDF
            api_result: Dictionary with keys 'title' and 'author' from API

        Returns:
            Overall confidence score from 0.0 to 1.0

        Raises:
            KeyError: If required fields ('title' or 'author') are missing
        """
        title_sim = MetadataMatchingService.title_similarity(
            extracted.get('title', ''),
            api_result.get('title', '')
        )
        author_sim = MetadataMatchingService.author_similarity(
            extracted.get('author', ''),
            api_result.get('author', '')
        )

        # Weighted formula: 60% title, 40% author
        overall = (title_sim * 0.6) + (author_sim * 0.4)

        return overall
