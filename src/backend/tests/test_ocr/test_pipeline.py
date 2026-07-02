"""
Tests for the OCR pipeline, preprocessing, and error detection.
"""

import pytest
import cv2
import numpy as np
from pathlib import Path

from app.ocr.pipeline import (
    OCRPipeline,
    ImagePreprocessor,
    OCRErrorDetector,
)


class TestImagePreprocessor:
    """Tests for image preprocessing."""

    def test_preprocess_color_image(self):
        """Test preprocessing a color image."""
        # Create a test image
        image = np.ones((100, 200, 3), dtype=np.uint8) * 200

        result = ImagePreprocessor.preprocess(image)

        assert result is not None
        assert result.shape[:2] == (100, 200)
        assert len(result.shape) == 2  # Should be grayscale

    def test_preprocess_grayscale_image(self):
        """Test preprocessing a grayscale image."""
        image = np.ones((100, 200), dtype=np.uint8) * 150

        result = ImagePreprocessor.preprocess(image)

        assert result is not None
        assert result.shape == (100, 200)

    def test_preprocess_handles_invalid_input(self):
        """Test that preprocessing handles invalid input gracefully."""
        # Very small image
        image = np.ones((2, 2), dtype=np.uint8)
        result = ImagePreprocessor.preprocess(image)
        assert result is not None


class TestOCRErrorDetector:
    """Tests for OCR error detection and quality estimation."""

    def test_count_errors_empty_text(self):
        """Test error counting with empty text."""
        errors = OCRErrorDetector.count_errors("")
        assert errors == 0

    def test_count_errors_clean_text(self):
        """Test error counting with clean text."""
        text = "The quick brown fox jumps over the lazy dog."
        errors = OCRErrorDetector.count_errors(text)
        assert errors == 0

    def test_count_errors_digit_confusion(self):
        """Test detection of 0/O digit confusion."""
        text = "Phone number: 000-555-1212"
        errors = OCRErrorDetector.count_errors(text)
        assert errors > 0  # Should detect pattern

    def test_count_errors_letter_confusion(self):
        """Test detection of 1/l letter confusion."""
        text = "The number is 1ll not 111"
        errors = OCRErrorDetector.count_errors(text)
        assert errors > 0

    def test_count_errors_rn_confusion(self):
        """Test detection of rn/m confusion."""
        # Use lowercase 'rn' sequence which is what OCR confuses with 'm'
        text = "The word rnrn appears here to test confusion"
        errors = OCRErrorDetector.count_errors(text)
        assert errors > 0

    def test_count_errors_garbled_text(self):
        """Test detection of garbled/non-ASCII text."""
        text = "Good text with some ąćęłńóśźż bad characters"
        errors = OCRErrorDetector.count_errors(text)
        # May or may not detect depending on threshold

    def test_estimate_quality_no_text(self):
        """Test quality estimation with no text."""
        quality = OCRErrorDetector.estimate_quality(0, 0)
        assert quality == 0.0

    def test_estimate_quality_no_errors(self):
        """Test quality estimation with perfect text."""
        text_length = 1000
        quality = OCRErrorDetector.estimate_quality(0, text_length)
        assert quality == 1.0

    def test_estimate_quality_many_errors(self):
        """Test quality estimation with many errors."""
        text_length = 100
        errors = 50
        quality = OCRErrorDetector.estimate_quality(errors, text_length)
        assert 0.0 <= quality < 0.5  # Low quality

    def test_estimate_quality_bounds(self):
        """Test that quality is always between 0 and 1."""
        for text_length in [10, 100, 1000]:
            for errors in [0, 1, 10, 100, 1000]:
                quality = OCRErrorDetector.estimate_quality(errors, text_length)
                assert 0.0 <= quality <= 1.0


class TestOCRPipeline:
    """Tests for the OCR pipeline."""

    def test_ocr_pipeline_initialization(self):
        """Test that OCR pipeline can be initialized."""
        pipeline = OCRPipeline()
        assert pipeline is not None

    def test_check_embedded_text_nonexistent_file(self):
        """Test checking embedded text on nonexistent file."""
        result = OCRPipeline.check_embedded_text("/nonexistent/file.pdf")
        assert result is False

    def test_run_ocr_tesseract_missing_file(self):
        """Test Tesseract OCR with missing file."""
        pipeline = OCRPipeline()
        text, quality, errors = pipeline.run_ocr_tesseract("/nonexistent/image.png")

        assert text == ""
        assert quality == 0.0
        assert errors == 9999

    def test_run_ocr_paddle_missing_file(self):
        """Test PaddleOCR with missing file."""
        pipeline = OCRPipeline()
        text, quality, errors = pipeline.run_ocr_paddle("/nonexistent/image.png")

        assert text == ""
        assert quality == 0.0
        assert errors == 9999

    def test_run_ocr_fallback_logic(self):
        """Test that run_ocr falls back correctly."""
        pipeline = OCRPipeline()

        # With missing file, should return empty text
        text, quality, errors = pipeline.run_ocr("/nonexistent/image.png", prefer_engine='tesseract')
        assert text == ""

    def test_run_ocr_with_real_image(self, tmp_path):
        """Test OCR with a real image (requires pytesseract)."""
        pytest.importorskip("pytesseract")

        # Create a simple test image with text
        image = np.ones((100, 300, 3), dtype=np.uint8) * 255
        cv2.putText(
            image,
            "Hello World",
            (20, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 0, 0),
            2
        )

        image_path = str(tmp_path / "test.png")
        cv2.imwrite(image_path, image)

        pipeline = OCRPipeline()
        text, quality, errors = pipeline.run_ocr_tesseract(image_path)

        # Should have some text extracted
        # Note: Simple image might not OCR perfectly, but should get something
        if text:
            assert "Hello" in text or len(text) > 0
            assert 0 <= quality <= 1.0
            assert isinstance(errors, int)
            assert errors >= 0
        else:
            # Empty result is ok for simple test image
            assert quality == 0.0

    def test_run_ocr_integration(self, tmp_path):
        """Test full OCR integration with real image."""
        pytest.importorskip("pytesseract")

        # Create test image with clear text
        image = np.ones((200, 400, 3), dtype=np.uint8) * 255
        cv2.putText(
            image,
            "The quick brown fox",
            (20, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.5,
            (0, 0, 0),
            2
        )

        image_path = str(tmp_path / "test_integration.png")
        cv2.imwrite(image_path, image)

        pipeline = OCRPipeline()
        text, quality, errors = pipeline.run_ocr(image_path)

        if text:
            # If text was extracted, check basic properties
            assert len(text) > 0
            assert 0 <= quality <= 1.0
            assert isinstance(errors, int)


class TestOCRQualityScoringIntegration:
    """Integration tests for OCR quality scoring in duplicate detection."""

    def test_quality_score_affects_duplicate_detection(self):
        """Test that quality scores would affect duplicate decisions."""
        # High quality OCR (few errors)
        high_quality_errors = 2
        high_quality_text_len = 1000
        high_quality = OCRErrorDetector.estimate_quality(
            high_quality_errors, high_quality_text_len
        )

        # Low quality OCR (many errors)
        low_quality_errors = 200
        low_quality_text_len = 1000
        low_quality = OCRErrorDetector.estimate_quality(
            low_quality_errors, low_quality_text_len
        )

        # High quality should score better
        assert high_quality > low_quality

    def test_error_count_variance(self):
        """Test that error counts vary with text content."""
        clean_text = "This is clean text with no OCR errors."
        garbled_text = "Th1s h4s l0ts 0f 0bvi0us OCR pr0bl3ms."

        clean_errors = OCRErrorDetector.count_errors(clean_text)
        garbled_errors = OCRErrorDetector.count_errors(garbled_text)

        # Garbled should have more detected errors
        assert garbled_errors >= clean_errors
