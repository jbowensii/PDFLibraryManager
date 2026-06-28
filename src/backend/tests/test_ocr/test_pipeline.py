"""Tests for OCR pipeline, preprocessing, and error detection."""

import pytest
import numpy as np
import cv2
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Tuple

from app.ocr.preprocessing import ImagePreprocessor
from app.ocr.error_detection import OCRErrorDetector
from app.ocr.pipeline import OCRPipeline


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def tmp_image_dir(tmp_path):
    """Create temporary directory for test images."""
    img_dir = tmp_path / "images"
    img_dir.mkdir()
    return img_dir


@pytest.fixture
def skewed_image():
    """Create a skewed image for deskew testing."""
    # Create a simple image with text-like pattern
    img = np.ones((400, 600, 3), dtype=np.uint8) * 255
    # Add some black rectangles that simulate text
    cv2.rectangle(img, (50, 50), (150, 100), (0, 0, 0), -1)
    cv2.rectangle(img, (200, 60), (300, 110), (0, 0, 0), -1)
    cv2.rectangle(img, (50, 150), (200, 200), (0, 0, 0), -1)

    # Apply rotation to create skew
    h, w = img.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, 15, 1.0)  # 15 degree rotation
    skewed = cv2.warpAffine(img, rotation_matrix, (w, h))

    return skewed


@pytest.fixture
def noisy_image():
    """Create a noisy image for denoise testing."""
    img = np.ones((400, 600, 3), dtype=np.uint8) * 255
    # Add black rectangles
    cv2.rectangle(img, (50, 50), (150, 100), (0, 0, 0), -1)
    cv2.rectangle(img, (200, 60), (300, 110), (0, 0, 0), -1)

    # Add Gaussian noise
    noise = np.random.normal(0, 25, img.shape).astype(np.uint8)
    noisy = cv2.add(img, noise)

    return noisy


@pytest.fixture
def grayscale_image():
    """Create a grayscale image for binarization testing."""
    img = np.ones((400, 600), dtype=np.uint8) * 200
    # Add some gradual grayscale variation
    for i in range(600):
        img[:, i] = int(200 - (i / 600) * 100)

    # Add black rectangles
    cv2.rectangle(img, (50, 50), (150, 100), 0, -1)
    cv2.rectangle(img, (200, 60), (300, 110), 50, -1)

    return img


@pytest.fixture
def ocr_pipeline():
    """Create OCR pipeline instance."""
    with patch('app.ocr.pipeline.PaddleOCR'):
        pipeline = OCRPipeline()
    return pipeline


# ============================================================================
# Tests for ImagePreprocessor
# ============================================================================


class TestImagePreprocessor:
    """Test image preprocessing methods."""

    def test_preprocess_deskew(self, skewed_image):
        """Test deskew correction on rotated image."""
        deskewed = ImagePreprocessor.deskew(skewed_image)

        # Verify output is an image
        assert isinstance(deskewed, np.ndarray)
        assert deskewed.shape == skewed_image.shape
        assert deskewed.dtype == skewed_image.dtype

    def test_preprocess_denoise(self, noisy_image):
        """Test noise reduction."""
        denoised = ImagePreprocessor.denoise(noisy_image)

        # Verify output is an image
        assert isinstance(denoised, np.ndarray)
        assert denoised.shape == noisy_image.shape

        # Verify noise is reduced (variance should decrease)
        original_variance = np.var(noisy_image.astype(float))
        denoised_variance = np.var(denoised.astype(float))
        assert denoised_variance < original_variance

    def test_preprocess_binarize(self, grayscale_image):
        """Test binarization to binary image."""
        binary = ImagePreprocessor.binarize(grayscale_image)

        # Verify output is binary (only 0 or 255)
        assert isinstance(binary, np.ndarray)
        unique_values = np.unique(binary)
        assert set(unique_values.tolist()).issubset({0, 255})

    def test_preprocess_binarize_color_image(self):
        """Test binarization with color image input."""
        # Create color image
        img = np.ones((300, 400, 3), dtype=np.uint8) * 150
        cv2.rectangle(img, (50, 50), (150, 100), (0, 0, 0), -1)

        binary = ImagePreprocessor.binarize(img)

        # Verify output is binary
        unique_values = np.unique(binary)
        assert set(unique_values.tolist()).issubset({0, 255})

    def test_preprocess_full_pipeline(self, skewed_image):
        """Test full preprocessing pipeline."""
        preprocessed = ImagePreprocessor.preprocess(skewed_image)

        # Verify output is binary
        assert isinstance(preprocessed, np.ndarray)
        unique_values = np.unique(preprocessed)
        assert set(unique_values.tolist()).issubset({0, 255})

    def test_denoise_grayscale(self):
        """Test denoise on grayscale image."""
        gray = np.ones((200, 300), dtype=np.uint8) * 128
        noise = np.random.normal(0, 20, gray.shape).astype(np.uint8)
        noisy_gray = cv2.add(gray, noise)

        denoised = ImagePreprocessor.denoise(noisy_gray)

        assert isinstance(denoised, np.ndarray)
        assert len(denoised.shape) == 2  # Grayscale


# ============================================================================
# Tests for OCRErrorDetector
# ============================================================================


class TestOCRErrorDetector:
    """Test OCR error detection and quality estimation."""

    def test_count_ocr_errors_with_unknowns(self):
        """Test error counting with [?] markers."""
        text = "This is a test [?] with unknowns [?] and [?] markers."
        error_count = OCRErrorDetector.count_errors(text)

        # Should detect [?] markers
        assert error_count > 0

    def test_count_ocr_errors_with_non_ascii(self):
        """Test error counting with non-ASCII characters."""
        text = "This has some gibberish: \x00\x01\x02 and weird chars: \xff\xfe"
        error_count = OCRErrorDetector.count_errors(text)

        # Should detect non-ASCII
        assert error_count > 0

    def test_count_ocr_errors_with_excessive_spaces(self):
        """Test error counting with excessive spaces."""
        text = "This has     excessive     spaces and some      gibberish."
        error_count = OCRErrorDetector.count_errors(text)

        # Should detect excessive spaces
        assert error_count > 0

    def test_count_ocr_errors_clean_text(self):
        """Test error counting with clean text."""
        text = "This is clean text with no errors. It has normal spacing and good characters."
        error_count = OCRErrorDetector.count_errors(text)

        # Should have no errors
        assert error_count == 0

    def test_count_ocr_errors_mixed(self):
        """Test error counting with mixed errors."""
        text = "Mixed errors [?] with non-ascii \x00\x01 and     excessive spaces."
        error_count = OCRErrorDetector.count_errors(text)

        # Should detect all types of errors
        assert error_count > 0

    def test_estimate_quality_perfect(self):
        """Test quality estimation for perfect text."""
        # No errors, any length
        quality = OCRErrorDetector.estimate_quality(0, 100)
        assert quality == 1.0

    def test_estimate_quality_degraded(self):
        """Test quality estimation for degraded text."""
        # Many errors relative to text length
        quality = OCRErrorDetector.estimate_quality(50, 100)
        # 50 errors / (100/100) = 50 error rate
        # quality = 1.0 - (50/10) = 1.0 - 5.0 = clamped to 0.0
        assert quality < 0.5

    def test_estimate_quality_empty_text(self):
        """Test quality estimation for empty text."""
        quality = OCRErrorDetector.estimate_quality(0, 0)
        assert quality == 0.0

    def test_estimate_quality_clamped_upper(self):
        """Test that quality is clamped to 1.0."""
        quality = OCRErrorDetector.estimate_quality(0, 1000)
        assert quality == 1.0

    def test_estimate_quality_clamped_lower(self):
        """Test that quality is clamped to 0.0."""
        quality = OCRErrorDetector.estimate_quality(1000, 100)
        # error_rate = 1000 / (100/100) = 1000
        # quality = 1.0 - (1000/10) = 1.0 - 100.0 = -99.0, clamped to 0.0
        assert quality == 0.0

    def test_estimate_quality_moderate(self):
        """Test quality estimation for moderate errors."""
        # 5 errors in 100 chars
        quality = OCRErrorDetector.estimate_quality(5, 100)
        # error_rate = 5 / (100/100) = 5
        # quality = 1.0 - (5/10) = 0.5
        assert quality == 0.5


# ============================================================================
# Tests for OCRPipeline
# ============================================================================


class TestOCRPipeline:
    """Test OCR pipeline methods."""

    def test_check_embedded_text_with_text(self, ocr_pipeline, tmp_path):
        """Test detection of embedded text in PDF."""
        # Create a mock PDF with text
        pdf_path = str(tmp_path / "test.pdf")

        with patch('app.ocr.pipeline.pdfplumber.open') as mock_pdf_open:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "This is a PDF with " + "x" * 600 + " characters of text"

            mock_pdf.pages = [mock_page, mock_page, mock_page]
            mock_pdf.__enter__.return_value = mock_pdf
            mock_pdf.__exit__.return_value = False
            mock_pdf_open.return_value = mock_pdf

            result = ocr_pipeline.check_embedded_text(pdf_path, threshold=500)

            assert result is True

    def test_check_embedded_text_without_text(self, ocr_pipeline, tmp_path):
        """Test detection of PDF without embedded text (scanned)."""
        pdf_path = str(tmp_path / "scanned.pdf")

        with patch('app.ocr.pipeline.pdfplumber.open') as mock_pdf_open:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Small text"

            mock_pdf.pages = [mock_page, mock_page, mock_page]
            mock_pdf.__enter__.return_value = mock_pdf
            mock_pdf.__exit__.return_value = False
            mock_pdf_open.return_value = mock_pdf

            result = ocr_pipeline.check_embedded_text(pdf_path, threshold=500)

            assert result is False

    def test_check_embedded_text_error_handling(self, ocr_pipeline, tmp_path):
        """Test error handling in embedded text check."""
        pdf_path = str(tmp_path / "broken.pdf")

        with patch('app.ocr.pipeline.pdfplumber.open') as mock_pdf_open:
            mock_pdf_open.side_effect = Exception("PDF corrupted")

            result = ocr_pipeline.check_embedded_text(pdf_path)

            assert result is False

    def test_run_ocr_tesseract_success(self, ocr_pipeline, tmp_path):
        """Test successful Tesseract OCR."""
        image_path = str(tmp_path / "test.png")

        with patch('app.ocr.pipeline.pytesseract.image_to_string') as mock_ocr:
            mock_ocr.return_value = "This is extracted text from Tesseract"

            text, quality, errors = ocr_pipeline.run_ocr_tesseract(image_path)

            assert text == "This is extracted text from Tesseract"
            assert isinstance(quality, float)
            assert 0.0 <= quality <= 1.0
            assert isinstance(errors, int)
            assert errors == 0

    def test_run_ocr_tesseract_error(self, ocr_pipeline, tmp_path):
        """Test Tesseract error handling."""
        image_path = str(tmp_path / "missing.png")

        with patch('app.ocr.pipeline.pytesseract.image_to_string') as mock_ocr:
            mock_ocr.side_effect = Exception("Tesseract not found")

            text, quality, errors = ocr_pipeline.run_ocr_tesseract(image_path)

            assert text == ""
            assert quality == 0.0
            assert errors == 9999

    def test_run_ocr_paddle_success(self, ocr_pipeline, tmp_path):
        """Test successful PaddleOCR."""
        image_path = str(tmp_path / "test.png")

        # Mock PaddleOCR - structure: [[[(bbox_points), text, confidence], ...]]
        ocr_pipeline.paddle_ocr = MagicMock()
        ocr_pipeline.paddle_ocr.ocr.return_value = [
            [
                (((0, 0), (100, 0), (100, 50), (0, 50)), ("Line one", 0.95)),
                (((0, 60), (100, 60), (100, 110), (0, 110)), ("Line two", 0.92)),
            ]
        ]

        text, quality, errors = ocr_pipeline.run_ocr_paddle(image_path)

        assert "Line one" in text or "Line two" in text
        assert isinstance(quality, float)
        assert 0.0 <= quality <= 1.0
        assert isinstance(errors, int)

    def test_run_ocr_paddle_no_model(self, ocr_pipeline, tmp_path):
        """Test PaddleOCR when model not initialized."""
        image_path = str(tmp_path / "test.png")
        ocr_pipeline.paddle_ocr = None

        text, quality, errors = ocr_pipeline.run_ocr_paddle(image_path)

        assert text == ""
        assert quality == 0.0
        assert errors == 9999

    def test_run_ocr_paddle_error(self, ocr_pipeline, tmp_path):
        """Test PaddleOCR error handling."""
        image_path = str(tmp_path / "test.png")

        ocr_pipeline.paddle_ocr = MagicMock()
        ocr_pipeline.paddle_ocr.ocr.side_effect = Exception("PaddleOCR failed")

        text, quality, errors = ocr_pipeline.run_ocr_paddle(image_path)

        assert text == ""
        assert quality == 0.0
        assert errors == 9999

    def test_multi_pass_ocr_high_confidence_tesseract(self, ocr_pipeline, tmp_path):
        """Test multi-pass OCR with high Tesseract confidence."""
        image_path = str(tmp_path / "clear.png")

        with patch.object(ocr_pipeline, 'run_ocr_tesseract') as mock_tess:
            with patch.object(ocr_pipeline, 'run_ocr_paddle') as mock_paddle:
                # Tesseract returns high quality
                mock_tess.return_value = ("Clear text from Tesseract", 0.95, 0)

                text, engine, quality, errors = ocr_pipeline.run_multi_pass_ocr(image_path)

                assert text == "Clear text from Tesseract"
                assert engine == "tesseract"
                assert quality == 0.95
                assert errors == 0
                # PaddleOCR should not be called
                mock_paddle.assert_not_called()

    def test_multi_pass_ocr_low_confidence_tesseract(self, ocr_pipeline, tmp_path):
        """Test multi-pass OCR with low Tesseract, fallback to PaddleOCR."""
        image_path = str(tmp_path / "blurry.png")

        with patch.object(ocr_pipeline, 'run_ocr_tesseract') as mock_tess:
            with patch.object(ocr_pipeline, 'run_ocr_paddle') as mock_paddle:
                # Tesseract returns low quality
                mock_tess.return_value = ("Blurry text [?] with errors", 0.6, 5)
                # PaddleOCR returns better result
                mock_paddle.return_value = ("Better text from PaddleOCR", 0.8, 2)

                text, engine, quality, errors = ocr_pipeline.run_multi_pass_ocr(image_path)

                assert text == "Better text from PaddleOCR"
                assert engine == "paddleocr"
                assert quality == 0.8
                assert errors == 2
                # Both should be called
                mock_tess.assert_called_once()
                mock_paddle.assert_called_once()

    def test_multi_pass_ocr_paddle_worse_result(self, ocr_pipeline, tmp_path):
        """Test multi-pass OCR preferring Tesseract when Paddle is worse."""
        image_path = str(tmp_path / "blurry.png")

        with patch.object(ocr_pipeline, 'run_ocr_tesseract') as mock_tess:
            with patch.object(ocr_pipeline, 'run_ocr_paddle') as mock_paddle:
                # Tesseract returns low quality but with few errors
                mock_tess.return_value = ("Low quality text", 0.6, 3)
                # PaddleOCR returns more errors
                mock_paddle.return_value = ("PaddleOCR text", 0.8, 5)

                text, engine, quality, errors = ocr_pipeline.run_multi_pass_ocr(image_path)

                # Should stick with Tesseract due to fewer errors
                assert text == "Low quality text"
                assert engine == "tesseract"
                assert quality == 0.6
                assert errors == 3

    def test_multi_pass_ocr_paddle_same_errors(self, ocr_pipeline, tmp_path):
        """Test multi-pass OCR when both have same error count."""
        image_path = str(tmp_path / "blurry.png")

        with patch.object(ocr_pipeline, 'run_ocr_tesseract') as mock_tess:
            with patch.object(ocr_pipeline, 'run_ocr_paddle') as mock_paddle:
                # Both return same error count
                mock_tess.return_value = ("Tesseract text", 0.6, 5)
                mock_paddle.return_value = ("PaddleOCR text", 0.8, 5)

                text, engine, quality, errors = ocr_pipeline.run_multi_pass_ocr(image_path)

                # Should use Tesseract (default/fallback)
                assert text == "Tesseract text"
                assert engine == "tesseract"


# ============================================================================
# Integration-style tests
# ============================================================================


class TestOCRIntegration:
    """Integration tests combining preprocessing and OCR."""

    def test_pipeline_creation(self):
        """Test that pipeline can be created."""
        with patch('app.ocr.pipeline.PaddleOCR'):
            pipeline = OCRPipeline()
            assert pipeline is not None

    def test_preprocessing_followed_by_quality_estimation(self, grayscale_image):
        """Test preprocessing output can be evaluated for quality."""
        # Preprocess image
        processed = ImagePreprocessor.preprocess(grayscale_image)

        # Simulate OCR would extract text from this
        # In reality, would pass to Tesseract
        assert processed.dtype in [np.uint8]
        assert len(processed.shape) == 2  # Binary output

    def test_quality_estimation_consistency(self):
        """Test quality estimation is consistent."""
        text = "This is sample text " + "x" * 500
        errors_low = OCRErrorDetector.count_errors(text)
        quality_high = OCRErrorDetector.estimate_quality(errors_low, len(text))

        text_bad = "Bad [?] text " + "\x00" * 50 + "     excessive spaces"
        errors_high = OCRErrorDetector.count_errors(text_bad)
        quality_low = OCRErrorDetector.estimate_quality(errors_high, len(text_bad))

        # Clean text should have better quality
        assert quality_high > quality_low
