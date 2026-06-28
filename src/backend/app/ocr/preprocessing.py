"""Image preprocessing for OCR quality enhancement."""

import cv2
import numpy as np


class ImagePreprocessor:
    """Static methods for preprocessing images before OCR."""

    @staticmethod
    def deskew(image: np.ndarray) -> np.ndarray:
        """
        Deskew an image by detecting rotation angle and correcting it.

        Uses convex hull and minimum area rectangle to calculate rotation angle,
        then applies affine transformation.

        Args:
            image: Input image as numpy array.

        Returns:
            Deskewed image.
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Threshold the image
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return image

        # Get convex hull of the largest contour
        largest_contour = max(contours, key=cv2.contourArea)
        hull = cv2.convexHull(largest_contour)

        # Get minimum area rectangle
        rect = cv2.minAreaRect(hull)
        angle = rect[2]

        # Normalize angle
        if angle < -45:
            angle = 90 + angle

        # Get image dimensions
        h, w = image.shape[:2]

        # Get rotation matrix
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

        # Apply affine transformation
        deskewed = cv2.warpAffine(
            image, rotation_matrix, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT
        )

        return deskewed

    @staticmethod
    def denoise(image: np.ndarray) -> np.ndarray:
        """
        Denoise an image using fast non-local means denoising.

        Args:
            image: Input image as numpy array.

        Returns:
            Denoised image.
        """
        # Convert to BGR if grayscale (fastNlMeansDenoising expects BGR)
        if len(image.shape) == 2:
            # Grayscale: use single-channel denoising
            denoised = cv2.fastNlMeansDenoising(image, None, h=10, templateWindowSize=7, searchWindowSize=21)
        else:
            # Color: use color denoising
            denoised = cv2.fastNlMeansDenoisingColored(
                image, None, h=10, templateWindowSize=7, searchWindowSize=21
            )

        return denoised

    @staticmethod
    def binarize(image: np.ndarray) -> np.ndarray:
        """
        Convert image to binary using adaptive thresholding.

        Args:
            image: Input image as numpy array.

        Returns:
            Binary image.
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Apply adaptive threshold
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

        return binary

    @staticmethod
    def preprocess(image: np.ndarray) -> np.ndarray:
        """
        Fully preprocess an image for OCR.

        Applies deskew, denoise, and binarize in sequence.

        Args:
            image: Input image as numpy array.

        Returns:
            Fully preprocessed image.
        """
        # Apply transformations in sequence
        deskewed = ImagePreprocessor.deskew(image)
        denoised = ImagePreprocessor.denoise(deskewed)
        binary = ImagePreprocessor.binarize(denoised)

        return binary
