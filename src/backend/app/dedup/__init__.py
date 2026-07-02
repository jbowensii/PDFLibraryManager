"""
Duplicate detection and resolution module.

Provides duplicate detection, scoring, and automated resolution services
for the PDF Library Manager.
"""

from .scoring import DuplicateScorer
from .detection import DuplicateDetectionService

__all__ = ['DuplicateScorer', 'DuplicateDetectionService']
