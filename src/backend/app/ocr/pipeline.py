"""
OCR pipeline for text extraction from PDFs.

Provides functionality to check for embedded text in PDFs,
preprocess images for OCR, run Tesseract and PaddleOCR engines,
and detect OCR errors for quality assessment.
"""

import logging
import re
from typing import Tuple
import cv2
import numpy as np
import pypdf

# Try to import OCR engines; gracefully handle if not installed
try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    from paddleocr import PaddleOCR
except ImportError:
    PaddleOCR = None

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """Preprocesses images for better OCR accuracy."""

    @staticmethod
    def preprocess(image: np.ndarray) -> np.ndarray:
        """
        Preprocess an image for OCR.

        Applies techniques to improve OCR accuracy:
        - Convert to grayscale if needed
        - Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        - Apply bilateral filtering for noise reduction
        - Apply thresholding for binarization

        Args:
            image: OpenCV image (BGR or grayscale)

        Returns:
            Preprocessed image ready for OCR
        """
        try:
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image

            # Apply CLAHE for adaptive histogram equalization
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)

            # Apply bilateral filtering to reduce noise while preserving edges
            denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)

            # Apply Otsu's thresholding for binarization
            _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            return binary
        except Exception as e:
            logger.warning(f"Preprocessing failed, returning original image: {e}")
            return image


class OCRErrorDetector:
    """Detects and counts OCR errors in extracted text."""

    # Common OCR error patterns
    COMMON_ERRORS = [
        (r'\b[0O][0O]{2,}\b', 'number-zero-confusion'),  # OOO, 000
        (r'\b[1l|!]{2,}\b', 'one-letter-confusion'),      # lll, |||
        (r'\b[rn]{2,}\b', 'rn-m-confusion'),              # rnrn
        (r'[^a-zA-Z0-9\s\.,;:\'\"\-\(\)]{5,}', 'special-char-run'),  # 5+ special chars
        (r'\b[A-Z]{10,}\b', 'all-caps-acronym'),          # Very long all-caps
    ]

    @staticmethod
    def count_errors(text: str) -> int:
        """
        Count suspected OCR errors in extracted text.

        Looks for common OCR error patterns including:
        - Digit/letter confusion (0/O, 1/l)
        - Common misrecognitions (rn as m, etc.)
        - Unusual character sequences
        - Garbled text patterns

        Args:
            text: Extracted text from OCR

        Returns:
            Estimated count of OCR errors
        """
        if not text or not text.strip():
            return 0

        error_count = 0

        for pattern, error_type in OCRErrorDetector.COMMON_ERRORS:
            matches = re.findall(pattern, text)
            error_count += len(matches)

        # Also count lines that are completely garbled
        # (more than 50% non-printable/non-ASCII characters)
        lines = text.split('\n')
        for line in lines:
            if len(line) > 5:  # Only check lines with meaningful length
                non_ascii_ratio = sum(1 for c in line if ord(c) > 127) / len(line)
                if non_ascii_ratio > 0.5:
                    error_count += 1

        return error_count

    @staticmethod
    def estimate_quality(error_count: int, text_length: int) -> float:
        """
        Estimate OCR quality as a score between 0.0 and 1.0.

        Quality = 1.0 - (error_count / max(text_length / 10, 1))
        Clamped to [0.0, 1.0]

        A longer text with same error count is higher quality.

        Args:
            error_count: Number of detected errors
            text_length: Length of extracted text

        Returns:
            Quality score from 0.0 (very low) to 1.0 (excellent)
        """
        if text_length == 0:
            return 0.0

        # Estimate: ~1 error per 10 characters in poor OCR
        estimated_max_errors = max(text_length / 10, 1)
        quality = 1.0 - (error_count / estimated_max_errors)

        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, quality))


class OCRPipeline:
    """Pipeline for OCR and embedded text extraction."""

    def __init__(self):
        """Initialize OCR pipeline with available engines."""
        self.paddle_ocr = None
        if PaddleOCR is not None:
            try:
                self.paddle_ocr = PaddleOCR(use_textline_orientation=True, lang='en')
                logger.info("PaddleOCR initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize PaddleOCR: {e}")

    @staticmethod
    def check_embedded_text(pdf_path: str) -> bool:
        """
        Check if a PDF has embedded text.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            True if the PDF has extractable embedded text, False otherwise
        """
        try:
            with open(pdf_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                if not reader.pages:
                    return False

                for page in reader.pages:
                    text = page.extract_text()
                    if text and text.strip():
                        return True

                return False
        except Exception as e:
            logger.warning(f"Error checking embedded text: {e}")
            return False

    def run_ocr_tesseract(self, image_path: str) -> Tuple[str, float, int]:
        """
        Run Tesseract OCR on an image.

        Args:
            image_path: Path to the image file

        Returns:
            Tuple of (extracted_text, quality_score, error_count)
            Returns ("", 0.0, 9999) on failure
        """
        if pytesseract is None:
            logger.error("Tesseract not available - pytesseract not installed")
            return "", 0.0, 9999

        try:
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Failed to read image: {image_path}")
                return "", 0.0, 9999

            # Preprocess image
            preprocessed = ImagePreprocessor.preprocess(image)

            # Run Tesseract
            text = pytesseract.image_to_string(preprocessed, lang="eng")

            if not text or not text.strip():
                return "", 0.0, 0

            # Count errors and estimate quality
            error_count = OCRErrorDetector.count_errors(text)
            quality = OCRErrorDetector.estimate_quality(error_count, len(text))

            logger.info(
                f"Tesseract OCR: {len(text)} chars, "
                f"{error_count} errors, quality={quality:.2f}"
            )

            return text, quality, error_count

        except Exception as e:
            logger.error(f"Tesseract OCR failed: {e}")
            return "", 0.0, 9999

    def run_ocr_paddle(self, image_path: str) -> Tuple[str, float, int]:
        """
        Run PaddleOCR on an image.

        Args:
            image_path: Path to the image file

        Returns:
            Tuple of (extracted_text, quality_score, error_count)
            Returns ("", 0.0, 9999) on failure
        """
        if self.paddle_ocr is None:
            logger.error("PaddleOCR not available")
            return "", 0.0, 9999

        try:
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Failed to read image: {image_path}")
                return "", 0.0, 9999

            # Preprocess image
            preprocessed = ImagePreprocessor.preprocess(image)

            # Run PaddleOCR
            result = self.paddle_ocr.ocr(preprocessed, cls=True)

            # Extract text from result structure
            # PaddleOCR returns: [[[bbox], [text, confidence]], ...]
            if result and result[0]:
                text = "\n".join([line[1][0] for line in result[0]])
            else:
                return "", 0.0, 0

            if not text or not text.strip():
                return "", 0.0, 0

            # Count errors and estimate quality
            error_count = OCRErrorDetector.count_errors(text)
            quality = OCRErrorDetector.estimate_quality(error_count, len(text))

            logger.info(
                f"PaddleOCR: {len(text)} chars, "
                f"{error_count} errors, quality={quality:.2f}"
            )

            return text, quality, error_count

        except Exception as e:
            logger.error(f"PaddleOCR failed: {e}")
            return "", 0.0, 9999

    def run_ocr(self, image_path: str, prefer_engine: str = 'tesseract') -> Tuple[str, float, int]:
        """
        Run OCR using the preferred engine, falling back to alternatives.

        Args:
            image_path: Path to the image file
            prefer_engine: 'tesseract' or 'paddle' (default: tesseract)

        Returns:
            Tuple of (extracted_text, quality_score, error_count)
        """
        if prefer_engine == 'paddle':
            text, quality, errors = self.run_ocr_paddle(image_path)
            if text:  # PaddleOCR succeeded
                return text, quality, errors
            # Fall back to Tesseract
            return self.run_ocr_tesseract(image_path)
        else:
            # Default: try Tesseract first
            text, quality, errors = self.run_ocr_tesseract(image_path)
            if text:  # Tesseract succeeded
                return text, quality, errors
            # Fall back to PaddleOCR
            return self.run_ocr_paddle(image_path)
