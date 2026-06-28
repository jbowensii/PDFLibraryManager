"""Application configuration."""

from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # App
    APP_NAME: str = "PDF Library Manager"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "your-secret-key-change-in-production"

    # Database
    DATABASE_URL: str = "postgresql://dev:devpass@localhost:5432/pdf_library"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # API
    API_PORT: int = 8000
    API_HOST: str = "0.0.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
    ]

    # Authentication
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"

    # File Storage
    LIBRARY_ROOT_PATH: str = "/library"
    NAMING_TEMPLATE: str = "{Publisher}/{Game}/{Game Name} {Title} - {ISBN} - {Publication Date}"
    MAX_UPLOAD_SIZE: int = 500_000_000  # 500MB

    # OCR Configuration
    OCR_LANGUAGE: str = "eng"
    OCR_CONFIDENCE_THRESHOLD: float = 0.7
    OCR_MAX_WORKERS: int = 3
    TESSERACT_PATH: str = "/usr/bin/tesseract"
    PADDLEOCR_USE_GPU: bool = False

    # Metadata Configuration
    GOOGLE_BOOKS_API_KEY: str = ""
    OPENLIB_API_URL: str = "https://openlibrary.org"
    METADATA_CONFIDENCE_THRESHOLD: float = 0.9

    # Celery Configuration
    CELERY_BROKER_URL: str = "redis://localhost:6379"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379"
    CELERY_CONCURRENCY: int = 4

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
