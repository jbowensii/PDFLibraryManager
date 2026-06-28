"""OCR error detection and quality estimation."""

import re
from typing import Tuple


class OCRErrorDetector:
    """Static methods for detecting OCR errors and estimating text quality."""

    @staticmethod
    def count_errors(text: str) -> int:
        """
        Count OCR errors in text using heuristic patterns.

        Detects:
        - [?] markers (undetermined characters)
        - Non-ASCII characters (OCR artifacts)
        - Excessive spaces (OCR artifacts)

        Args:
            text: Input text from OCR.

        Returns:
            Total error count (sum of all error patterns).
        """
        error_count = 0

        # Count [?] markers (undetermined characters)
        unknown_markers = len(re.findall(r'\[?\?\]?', text))
        error_count += unknown_markers

        # Count non-ASCII characters (likely OCR artifacts)
        non_ascii = len(re.findall(r'[^\x20-\x7E\n]', text))
        error_count += non_ascii

        # Count excessive spaces (5+ consecutive spaces)
        excessive_spaces = len(re.findall(r'[ ]{5,}', text))
        error_count += excessive_spaces

        return error_count

    @staticmethod
    def estimate_quality(error_count: int, text_length: int) -> float:
        """
        Estimate OCR quality score based on error count.

        Returns a value between 0.0 (completely failed) and 1.0 (perfect).

        Args:
            error_count: Number of detected errors.
            text_length: Length of the extracted text.

        Returns:
            Quality score (0.0-1.0).
        """
        if text_length == 0:
            return 0.0

        # Calculate error rate (errors per 100 characters)
        error_rate = error_count / (text_length / 100)

        # Calculate quality: 1.0 - normalized error rate
        # Dividing by 10 means 10+ errors per 100 chars = 0% quality
        quality = max(0.0, 1.0 - (error_rate / 10))

        # Clamp to 0.0-1.0
        return min(1.0, quality)
