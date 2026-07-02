"""
Metadata lookup service for querying book information from multiple APIs.

Supports ISBN lookups via Open Library and title/author searches via
Open Library and Google Books APIs. Provides graceful error handling
and timeouts to prevent blocking on network failures.
"""

from typing import Optional, Dict
import requests
from urllib.parse import quote


class MetadataLookupService:
    """Service for looking up book metadata from external APIs."""

    # API configuration constants
    OPENLIBRARY_ISBN_URL = "https://openlibrary.org/isbn/{isbn}.json"
    OPENLIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
    GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"
    API_TIMEOUT = 5  # seconds

    @staticmethod
    def lookup_isbn_openlibrary(isbn: str) -> Optional[Dict]:
        """
        Look up book metadata by ISBN using Open Library API.

        Open Library ISBN lookups are fast and reliable. Returns the most
        accurate matches since ISBN is a unique identifier.

        Args:
            isbn: ISBN-10 or ISBN-13 to look up

        Returns:
            Dictionary with keys: title, author, publisher, isbn, publish_date
            Returns None if ISBN not found or on API error/timeout

        Example:
            >>> result = MetadataLookupService.lookup_isbn_openlibrary("9780451524935")
            >>> result['title'] if result else None
            'The Great Gatsby'
        """
        try:
            url = MetadataLookupService.OPENLIBRARY_ISBN_URL.format(isbn=isbn)
            response = requests.get(url, timeout=MetadataLookupService.API_TIMEOUT)

            # 404 is expected for invalid ISBNs
            if response.status_code == 404:
                return None

            response.raise_for_status()
            data = response.json()

            # Parse response
            title = data.get('title', '')
            authors = data.get('authors', [])
            author = ', '.join([a.get('name', '') for a in authors]) if authors else ''
            publishers = data.get('publishers', [])
            publisher = publishers[0] if publishers else ''
            publish_date = data.get('publish_date', '')

            return {
                'title': title,
                'author': author,
                'publisher': publisher,
                'isbn': isbn,
                'publish_date': publish_date
            }

        except requests.exceptions.Timeout:
            return None
        except requests.exceptions.RequestException:
            return None
        except (KeyError, ValueError, TypeError):
            return None

    @staticmethod
    def lookup_title_author_openlibrary(title: str, author: str) -> Optional[Dict]:
        """
        Look up book metadata by title and author using Open Library search.

        Combines title and author in search for better matching. Returns
        first result if found.

        Args:
            title: Book title to search for
            author: Author name to search for

        Returns:
            Dictionary with keys: title, author, publisher, isbn, publish_date
            Returns None if no results found or on API error/timeout

        Example:
            >>> result = MetadataLookupService.lookup_title_author_openlibrary(
            ...     "The Great Gatsby", "F. Scott Fitzgerald")
            >>> result['isbn'] if result else None
        """
        try:
            params = {
                'title': title,
                'author': author
            }
            response = requests.get(
                MetadataLookupService.OPENLIBRARY_SEARCH_URL,
                params=params,
                timeout=MetadataLookupService.API_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()

            # Check if we have results
            docs = data.get('docs', [])
            if not docs:
                return None

            # Return first result
            doc = docs[0]
            title = doc.get('title', '')
            authors = doc.get('author_name', [])
            author = ', '.join(authors) if authors else ''
            publishers = doc.get('publisher', [])
            publisher = publishers[0] if publishers else ''

            # Get first ISBN if available
            isbns = doc.get('isbn', [])
            isbn = isbns[0] if isbns else ''

            publish_date = doc.get('first_publish_year', '')
            if publish_date:
                publish_date = str(publish_date)

            return {
                'title': title,
                'author': author,
                'publisher': publisher,
                'isbn': isbn,
                'publish_date': publish_date
            }

        except requests.exceptions.Timeout:
            return None
        except requests.exceptions.RequestException:
            return None
        except (KeyError, ValueError, TypeError):
            return None

    @staticmethod
    def lookup_google_books(title: str, author: str, api_key: Optional[str] = None) -> Optional[Dict]:
        """
        Look up book metadata using Google Books API.

        Google Books provides broad coverage but requires an API key for
        higher rate limits. Falls back gracefully if no results found.

        Args:
            title: Book title to search for
            author: Author name to search for
            api_key: Optional Google Books API key for higher rate limits

        Returns:
            Dictionary with keys: title, author, publisher, isbn, publish_date
            Returns None if no results found or on API error/timeout

        Example:
            >>> result = MetadataLookupService.lookup_google_books(
            ...     "The Great Gatsby", "F. Scott Fitzgerald")
            >>> result['title'] if result else None
        """
        try:
            # Build query with intitle and inauthor parameters for specificity
            query = f"intitle:{quote(title)}+inauthor:{quote(author)}"
            params = {
                'q': query,
                'maxResults': 1
            }

            # Add API key if provided
            if api_key:
                params['key'] = api_key

            response = requests.get(
                MetadataLookupService.GOOGLE_BOOKS_URL,
                params=params,
                timeout=MetadataLookupService.API_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()

            # Check if we have results
            items = data.get('items', [])
            if not items:
                return None

            # Parse first result
            volume_info = items[0].get('volumeInfo', {})
            title = volume_info.get('title', '')
            authors = volume_info.get('authors', [])
            author = ', '.join(authors) if authors else ''
            publisher = volume_info.get('publisher', '')
            publish_date = volume_info.get('publishedDate', '')

            # Extract ISBN from industryIdentifiers
            isbn = ''
            identifiers = volume_info.get('industryIdentifiers', [])
            for identifier in identifiers:
                if identifier.get('type') in ('ISBN_13', 'ISBN_10'):
                    isbn = identifier.get('identifier', '')
                    break

            return {
                'title': title,
                'author': author,
                'publisher': publisher,
                'isbn': isbn,
                'publish_date': publish_date
            }

        except requests.exceptions.Timeout:
            return None
        except requests.exceptions.RequestException:
            return None
        except (KeyError, ValueError, TypeError):
            return None
