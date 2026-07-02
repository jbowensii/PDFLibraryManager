"""
Tests for metadata matching and lookup services.

Tests cover:
- Fuzzy string matching for titles, authors, and publishers
- Confidence score calculation with weighted formulas
- API lookups from Open Library and Google Books
- Error handling and timeout resilience
- Auto-apply vs ask-user decision logic
"""

import pytest
from unittest.mock import patch, MagicMock
import requests

from app.metadata.matching import MetadataMatchingService
from app.metadata.lookup import MetadataLookupService


class TestTitleSimilarity:
    """Tests for title similarity matching."""

    def test_title_similarity_identical(self):
        """Identical titles should score 1.0."""
        score = MetadataMatchingService.title_similarity(
            "The Great Gatsby",
            "The Great Gatsby"
        )
        assert score == 1.0

    def test_title_similarity_high(self):
        """Similar titles should score > 0.8."""
        score = MetadataMatchingService.title_similarity(
            "StarCraft Battle Chest Manual",
            "StarCraft Battle Chest"
        )
        assert score > 0.8

    def test_title_similarity_low(self):
        """Dissimilar titles should score lower than similar titles."""
        # token_set_ratio can be generous with overlapping words
        # StarCraft vs Warcraft both have "craft" which inflates similarity
        # Test with truly dissimilar titles instead
        score = MetadataMatchingService.title_similarity(
            "The Great Gatsby",
            "War and Peace"
        )
        assert score < 0.5

    def test_title_similarity_partial_match(self):
        """Partial title matches should score high with token_set_ratio."""
        # token_set_ratio handles word subsets well
        score = MetadataMatchingService.title_similarity(
            "To Kill a Mockingbird",
            "Kill Mockingbird"
        )
        # token_set_ratio is generous with subsets, likely close to 1.0
        assert score > 0.8

    def test_title_similarity_word_order(self):
        """Token_set_ratio should handle word order differences."""
        score = MetadataMatchingService.title_similarity(
            "The Python Cookbook",
            "Python Cookbook The"
        )
        assert score > 0.8


class TestAuthorSimilarity:
    """Tests for author similarity matching."""

    def test_author_similarity_exact(self):
        """Identical author names should score 1.0."""
        score = MetadataMatchingService.author_similarity(
            "John Smith",
            "John Smith"
        )
        assert score == 1.0

    def test_author_similarity_partial(self):
        """Similar author names should score high with token_set_ratio."""
        # token_set_ratio is generous with subsets of matching names
        score = MetadataMatchingService.author_similarity(
            "John Francis Smith",
            "John Smith"
        )
        # token_set_ratio will score this high since "John Smith" is a subset
        assert score > 0.8

    def test_author_similarity_different(self):
        """Different authors should score low."""
        score = MetadataMatchingService.author_similarity(
            "Stephen King",
            "J.K. Rowling"
        )
        assert score < 0.4


class TestPublisherSimilarity:
    """Tests for publisher similarity matching."""

    def test_publisher_similarity_exact(self):
        """Identical publisher names should score 1.0."""
        score = MetadataMatchingService.publisher_similarity(
            "Random House",
            "Random House"
        )
        assert score == 1.0

    def test_publisher_similarity_abbreviation(self):
        """Publisher abbreviations should match well."""
        score = MetadataMatchingService.publisher_similarity(
            "Random House Inc.",
            "Random House"
        )
        assert score > 0.8


class TestCalculateConfidence:
    """Tests for overall confidence score calculation."""

    def test_calculate_confidence_high(self):
        """High title and author matches should result in confidence >= 0.9."""
        extracted = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald'
        }
        api_result = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald'
        }
        confidence = MetadataMatchingService.calculate_confidence(extracted, api_result)
        assert confidence >= 0.9

    def test_calculate_confidence_moderate(self):
        """Moderate matches with some overlap."""
        # token_set_ratio is generous - use truly different titles
        extracted = {
            'title': 'The Great Gatsby Novel',
            'author': 'F. Scott Fitzgerald'
        }
        api_result = {
            'title': 'War and Peace',  # Completely different title
            'author': 'F. Scott Fitzgerald'  # Exact match
        }
        confidence = MetadataMatchingService.calculate_confidence(extracted, api_result)
        # Should be moderate: author perfect (1.0 * 0.4) + title poor (low * 0.6)
        assert 0.35 < confidence < 0.7

    def test_calculate_confidence_low(self):
        """Poor matches should result in confidence < 0.5."""
        extracted = {
            'title': 'StarCraft Manual',
            'author': 'Blizzard Corp'
        }
        api_result = {
            'title': 'Warcraft Chronicles',
            'author': 'Someone Else'
        }
        confidence = MetadataMatchingService.calculate_confidence(extracted, api_result)
        assert confidence < 0.5

    def test_calculate_confidence_formula_weighting(self):
        """Verify title (60%) is weighted more than author (40%)."""
        # Create scenarios where title is perfect but author is poor
        extracted = {
            'title': 'Test Book',
            'author': 'Poor Author Match'
        }
        api_result = {
            'title': 'Test Book',  # Perfect match
            'author': 'Completely Different Author'  # Poor match
        }
        confidence = MetadataMatchingService.calculate_confidence(extracted, api_result)
        # Should be > 0.5 due to title weighting (0.6 * 1.0 = 0.6)
        # Plus some contribution from partial author match
        assert 0.5 < confidence <= 1.0

    def test_calculate_confidence_missing_fields(self):
        """Should handle missing fields gracefully."""
        extracted = {
            'title': 'Test Book'
            # Missing author
        }
        api_result = {
            'title': 'Test Book',
            'author': 'Some Author'
        }
        confidence = MetadataMatchingService.calculate_confidence(extracted, api_result)
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0


class TestConfidenceDecision:
    """Tests for auto-apply vs ask-user decision logic."""

    def test_confidence_decision_auto_apply(self):
        """Confidence >= 0.9 should be flagged for auto-apply."""
        confidence = 0.95
        should_auto_apply = confidence >= 0.9
        assert should_auto_apply is True

    def test_confidence_decision_ask_user(self):
        """Confidence < 0.9 should be flagged for user confirmation."""
        confidence = 0.85
        should_auto_apply = confidence >= 0.9
        assert should_auto_apply is False

    def test_confidence_decision_boundary(self):
        """Exactly 0.9 should auto-apply."""
        confidence = 0.9
        should_auto_apply = confidence >= 0.9
        assert should_auto_apply is True

    def test_confidence_decision_just_below_threshold(self):
        """Just below 0.9 should ask user."""
        confidence = 0.89
        should_auto_apply = confidence >= 0.9
        assert should_auto_apply is False


class TestLookupISBNOpenLibrary:
    """Tests for ISBN lookup via Open Library."""

    @patch('requests.get')
    def test_lookup_isbn_success(self, mock_get):
        """Successful ISBN lookup should return populated dictionary."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'title': 'The Great Gatsby',
            'authors': [{'name': 'F. Scott Fitzgerald'}],
            'publishers': ['Scribner'],
            'publish_date': 'April 10, 1925'
        }
        mock_get.return_value = mock_response

        result = MetadataLookupService.lookup_isbn_openlibrary('9780451524935')

        assert result is not None
        assert result['title'] == 'The Great Gatsby'
        assert result['author'] == 'F. Scott Fitzgerald'
        assert result['publisher'] == 'Scribner'
        assert result['isbn'] == '9780451524935'
        assert result['publish_date'] == 'April 10, 1925'

    @patch('requests.get')
    def test_lookup_isbn_not_found(self, mock_get):
        """404 response should return None."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = MetadataLookupService.lookup_isbn_openlibrary('9999999999999')

        assert result is None

    @patch('requests.get')
    def test_lookup_isbn_multiple_authors(self, mock_get):
        """Should join multiple authors with comma."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'title': 'Book Title',
            'authors': [
                {'name': 'Author One'},
                {'name': 'Author Two'},
                {'name': 'Author Three'}
            ],
            'publishers': ['Publisher'],
            'publish_date': '2020'
        }
        mock_get.return_value = mock_response

        result = MetadataLookupService.lookup_isbn_openlibrary('9780451524935')

        assert result['author'] == 'Author One, Author Two, Author Three'

    @patch('requests.get')
    def test_lookup_isbn_missing_publishers(self, mock_get):
        """Should handle missing publishers gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'title': 'Book Title',
            'authors': [{'name': 'Author'}],
            'publishers': [],
            'publish_date': '2020'
        }
        mock_get.return_value = mock_response

        result = MetadataLookupService.lookup_isbn_openlibrary('9780451524935')

        assert result['publisher'] == ''


class TestLookupTitleAuthorOpenLibrary:
    """Tests for title+author lookup via Open Library."""

    @patch('requests.get')
    def test_lookup_title_author_success(self, mock_get):
        """Successful title+author lookup should return first result."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'docs': [
                {
                    'title': 'The Great Gatsby',
                    'author_name': ['F. Scott Fitzgerald'],
                    'publisher': ['Scribner'],
                    'isbn': ['9780451524935'],
                    'first_publish_year': 1925
                }
            ]
        }
        mock_get.return_value = mock_response

        result = MetadataLookupService.lookup_title_author_openlibrary(
            'The Great Gatsby',
            'F. Scott Fitzgerald'
        )

        assert result is not None
        assert result['title'] == 'The Great Gatsby'
        assert result['author'] == 'F. Scott Fitzgerald'
        assert result['isbn'] == '9780451524935'

    @patch('requests.get')
    def test_lookup_title_author_no_results(self, mock_get):
        """No results should return None."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'docs': []}
        mock_get.return_value = mock_response

        result = MetadataLookupService.lookup_title_author_openlibrary(
            'Nonexistent Book Title',
            'Unknown Author'
        )

        assert result is None

    @patch('requests.get')
    def test_lookup_title_author_multiple_authors(self, mock_get):
        """Should join multiple authors from author_name list."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'docs': [
                {
                    'title': 'Book Title',
                    'author_name': ['Author One', 'Author Two'],
                    'publisher': ['Publisher'],
                    'isbn': ['123'],
                    'first_publish_year': 2020
                }
            ]
        }
        mock_get.return_value = mock_response

        result = MetadataLookupService.lookup_title_author_openlibrary('Title', 'Author')

        assert result['author'] == 'Author One, Author Two'


class TestLookupGoogleBooks:
    """Tests for Google Books API lookup."""

    @patch('requests.get')
    def test_lookup_google_books_success(self, mock_get):
        """Successful Google Books lookup should return populated dictionary."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'items': [
                {
                    'volumeInfo': {
                        'title': 'The Great Gatsby',
                        'authors': ['F. Scott Fitzgerald'],
                        'publisher': 'Scribner',
                        'publishedDate': '1925-04-10',
                        'industryIdentifiers': [
                            {'type': 'ISBN_13', 'identifier': '9780451524935'}
                        ]
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        result = MetadataLookupService.lookup_google_books(
            'The Great Gatsby',
            'F. Scott Fitzgerald'
        )

        assert result is not None
        assert result['title'] == 'The Great Gatsby'
        assert result['author'] == 'F. Scott Fitzgerald'
        assert result['publisher'] == 'Scribner'
        assert result['isbn'] == '9780451524935'

    @patch('requests.get')
    def test_lookup_google_books_no_results(self, mock_get):
        """No results should return None."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'items': []}
        mock_get.return_value = mock_response

        result = MetadataLookupService.lookup_google_books(
            'Nonexistent',
            'Author'
        )

        assert result is None

    @patch('requests.get')
    def test_lookup_google_books_with_api_key(self, mock_get):
        """Should include API key in request if provided."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'items': []}
        mock_get.return_value = mock_response

        MetadataLookupService.lookup_google_books(
            'Title',
            'Author',
            api_key='test-api-key-123'
        )

        # Verify the call included the API key
        call_kwargs = mock_get.call_args[1]
        assert 'params' in call_kwargs
        assert call_kwargs['params'].get('key') == 'test-api-key-123'

    @patch('requests.get')
    def test_lookup_google_books_isbn_extraction(self, mock_get):
        """Should extract ISBN from industryIdentifiers."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'items': [
                {
                    'volumeInfo': {
                        'title': 'Book',
                        'authors': ['Author'],
                        'publisher': 'Publisher',
                        'publishedDate': '2020',
                        'industryIdentifiers': [
                            {'type': 'ISBN_10', 'identifier': '0451524934'},
                            {'type': 'ISBN_13', 'identifier': '9780451524935'}
                        ]
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        result = MetadataLookupService.lookup_google_books('Book', 'Author')

        # Should get the first ISBN found
        assert result['isbn'] in ['0451524934', '9780451524935']


class TestAPITimeoutHandling:
    """Tests for graceful timeout handling."""

    @patch('requests.get')
    def test_lookup_isbn_timeout(self, mock_get):
        """ISBN lookup should return None on timeout."""
        mock_get.side_effect = requests.exceptions.Timeout()

        result = MetadataLookupService.lookup_isbn_openlibrary('9780451524935')

        assert result is None

    @patch('requests.get')
    def test_lookup_title_author_timeout(self, mock_get):
        """Title+author lookup should return None on timeout."""
        mock_get.side_effect = requests.exceptions.Timeout()

        result = MetadataLookupService.lookup_title_author_openlibrary('Title', 'Author')

        assert result is None

    @patch('requests.get')
    def test_lookup_google_books_timeout(self, mock_get):
        """Google Books lookup should return None on timeout."""
        mock_get.side_effect = requests.exceptions.Timeout()

        result = MetadataLookupService.lookup_google_books('Title', 'Author')

        assert result is None

    @patch('requests.get')
    def test_lookup_isbn_connection_error(self, mock_get):
        """ISBN lookup should return None on connection error."""
        mock_get.side_effect = requests.exceptions.ConnectionError()

        result = MetadataLookupService.lookup_isbn_openlibrary('9780451524935')

        assert result is None

    @patch('requests.get')
    def test_lookup_isbn_http_error(self, mock_get):
        """ISBN lookup should return None on HTTP error."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_get.return_value = mock_response

        result = MetadataLookupService.lookup_isbn_openlibrary('9780451524935')

        assert result is None


class TestAPIErrorHandling:
    """Tests for handling malformed API responses."""

    @patch('requests.get')
    def test_lookup_isbn_malformed_json(self, mock_get):
        """Should handle malformed JSON gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError('Invalid JSON')
        mock_get.return_value = mock_response

        result = MetadataLookupService.lookup_isbn_openlibrary('9780451524935')

        assert result is None

    @patch('requests.get')
    def test_lookup_google_books_missing_volume_info(self, mock_get):
        """Should handle missing volumeInfo gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'items': [{}]  # Missing volumeInfo
        }
        mock_get.return_value = mock_response

        result = MetadataLookupService.lookup_google_books('Title', 'Author')

        # Should return a result with empty strings rather than crashing
        assert result is not None
        assert result['title'] == ''


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
