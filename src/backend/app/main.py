"""
PDF Library Manager - FastAPI main application.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import router
from app.config import settings
from app.database import engine
from app.models import Base

# Create FastAPI app
app = FastAPI(
    title="PDF Library Manager API",
    description="API for managing PDF libraries with metadata, OCR, and deduplication",
    version="0.1.0",
)


@app.on_event("startup")
def create_tables() -> None:
    """Create database tables on startup (idempotent)."""
    Base.metadata.create_all(bind=engine)

# Add CORS middleware to allow frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint for load balancers and monitoring.

    Returns:
        dict: Service status and version information
    """
    return {
        "status": "ok",
        "service": "PDF Library Manager API",
        "version": "0.1.0",
    }


# API v1 root
@app.get("/api/v1")
async def api_root():
    """
    API v1 root endpoint.

    Returns:
        dict: API information and available endpoints
    """
    return {
        "message": "PDF Library Manager API v1",
        "endpoints": {
            "auth": "/api/v1/auth",
            "library": "/api/v1/library",
            "books": "/api/v1/books",
            "collections": "/api/v1/collections",
            "docs": "/docs",
            "redoc": "/redoc",
        },
    }


# Include API routers
app.include_router(router, prefix="/api/v1", tags=["api"])


# Root endpoint for diagnostics
@app.get("/")
async def root():
    """
    Root endpoint providing service information.

    Returns:
        dict: Service details
    """
    return {
        "service": "PDF Library Manager API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
