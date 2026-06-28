"""Multi-pass OCR pipeline with Tesseract and PaddleOCR."""

from typing import Tuple
import logging

import pytesseract
import pdfplumber
from paddleocr import PaddleOCR

from app.ocr.error_detection import OCRErrorDetector

logger = logging.getLogger(__name__)


class OCRPipeline:
    """Orchestrates multi-pass OCR with fallback strategy."""

    def __init__(self):
        """Initialize OCR pipeline with PaddleOCR model."""
        try:
            self.paddle_ocr = PaddleOCR(use_gpu=False, lang="en")
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {e}")
            self.paddle_ocr = None

    def check_embedded_text(self, pdf_path: str, threshold: int = 500) -> bool:
        """
        Check if PDF already has embedded text.

        Samples first 3 pages and checks if any contains more than threshold characters.

        Args:
            pdf_path: Path to PDF file.
            threshold: Character count threshold (default 500).

        Returns:
            True if PDF has embedded text above threshold, False otherwise.
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Check first 3 pages
                for page_num in range(min(3, len(pdf.pages))):
                    page = pdf.pages[page_num]
                    text = page.extract_text()

                    if text and len(text.strip()) > threshold:
                        return True

            return False

        except Exception as e:
            logger.error(f"Error checking embedded text in {pdf_path}: {e}")
            return False

    def run_ocr_tesseract(self, image_path: str) -> Tuple[str, float, int]:
        """
        Run OCR using Tesseract.

        Args:
            image_path: Path to image file.

        Returns:
            Tuple of (extracted_text, confidence_score, error_count).
            On exception: ("", 0.0, 9999).
        """
        try:
            text = pytesseract.image_to_string(image_path, lang="eng")

            # Count errors
            error_count = OCRErrorDetector.count_errors(text)

            # Estimate quality
            quality = OCRErrorDetector.estimate_quality(error_count, len(text))

            return text, quality, error_count

        except Exception as e:
            logger.error(f"Tesseract OCR failed for {image_path}: {e}")
            return "", 0.0, 9999

    def run_ocr_paddle(self, image_path: str) -> Tuple[str, float, int]:
        """
        Run OCR using PaddleOCR.

        Args:
            image_path: Path to image file.

        Returns:
            Tuple of (extracted_text, confidence_score, error_count).
            On exception: ("", 0.0, 9999).
        """
        try:
            if self.paddle_ocr is None:
                logger.error("PaddleOCR not initialized")
                return "", 0.0, 9999

            result = self.paddle_ocr.ocr(image_path, cls=True)

            # Extract text from result
            # PaddleOCR returns: [[[bbox_points], [text, confidence]], ...]
            if result and result[0]:
                text_parts = []
                for line in result[0]:
                    # Each line is [bbox, [text, confidence]]
                    if isinstance(line, (tuple, list)) and len(line) >= 2:
                        # line[1] could be [text, confidence] or (text, confidence)
                        text_item = line[1]
                        if isinstance(text_item, (list, tuple)):
                            text_parts.append(str(text_item[0]))
                        else:
                            text_parts.append(str(text_item))
                text = "\n".join(text_parts)
            else:
                text = ""

            # Count errors
            error_count = OCRErrorDetector.count_errors(text)

            # Estimate quality
            quality = OCRErrorDetector.estimate_quality(error_count, len(text))

            return text, quality, error_count

        except Exception as e:
            logger.error(f"PaddleOCR failed for {image_path}: {e}")
            return "", 0.0, 9999

    def run_multi_pass_ocr(self, image_path: str) -> Tuple[str, str, float, int]:
        """
        Run multi-pass OCR with fallback strategy.

        Pass 1: Tesseract (fast)
        Pass 2: PaddleOCR if Tesseract confidence < 70%

        Args:
            image_path: Path to image file.

        Returns:
            Tuple of (ocr_text, engine_used, confidence, error_count).
        """
        # Pass 1: Run Tesseract
        text_t, quality_t, errors_t = self.run_ocr_tesseract(image_path)

        logger.info(
            f"Tesseract OCR: quality={quality_t:.2f}, errors={errors_t}, text_len={len(text_t)}"
        )

        # Pass 2: Try PaddleOCR if Tesseract quality is low
        if quality_t < 0.7:
            text_p, quality_p, errors_p = self.run_ocr_paddle(image_path)

            logger.info(
                f"PaddleOCR OCR: quality={quality_p:.2f}, errors={errors_p}, text_len={len(text_p)}"
            )

            # Use PaddleOCR if it has fewer errors
            if errors_p < errors_t:
                return text_p, "paddleocr", quality_p, errors_p

        # Fallback to Tesseract
        return text_t, "tesseract", quality_t, errors_t
