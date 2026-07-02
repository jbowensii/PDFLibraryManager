"""
Configuration settings for the PDF Library Manager backend.
"""

import os
from pathlib import Path


class Settings:
    """Application settings."""

    # Debug / logging
    DEBUG = os.getenv('DEBUG', 'false').lower() in ('1', 'true', 'yes')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    # Database
    DATABASE_URL = os.getenv(
        'DATABASE_URL',
        'sqlite:///./pdf_library.db'
    )

    # Celery
    CELERY_BROKER_URL = os.getenv(
        'CELERY_BROKER_URL',
        'redis://localhost:6379/0'
    )
    CELERY_RESULT_BACKEND = os.getenv(
        'CELERY_RESULT_BACKEND',
        'redis://localhost:6379/1'
    )

    # Library
    LIBRARY_ROOT_PATH = os.getenv(
        'LIBRARY_ROOT_PATH',
        str(Path.home() / 'Documents' / 'PDFLibrary')
    )

    # API
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    ALGORITHM = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES = 30


settings = Settings()
