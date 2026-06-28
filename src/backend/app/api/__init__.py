"""API v1 router."""

from fastapi import APIRouter

from .auth import router as auth_router
from .books import router as books_router

router = APIRouter()

# Include authentication router
router.include_router(auth_router, prefix="/auth", tags=["Authentication"])

# Include books router
router.include_router(books_router, prefix="/books", tags=["Books"])

# These will be implemented in subsequent steps
# from .library import router as library_router
# from .search import router as search_router
# from .collections import router as collections_router
# from .duplicates import router as duplicates_router
# from .admin import router as admin_router
# router.include_router(library_router, prefix="/library", tags=["Library"])
# router.include_router(search_router, prefix="/search", tags=["Search"])
# router.include_router(collections_router, prefix="/collections", tags=["Collections"])
# router.include_router(duplicates_router, prefix="/duplicates", tags=["Duplicates"])
# router.include_router(admin_router, prefix="/admin", tags=["Admin"])


@router.get("/")
async def api_root():
    """API v1 root endpoint."""
    return {
        "message": "PDF Library Manager API v1",
        "endpoints": {
            "auth": "/api/v1/auth",
            "books": "/api/v1/books",
            "library": "/api/v1/library",
            "search": "/api/v1/search",
            "collections": "/api/v1/collections",
            "duplicates": "/api/v1/duplicates",
            "admin": "/api/v1/admin",
        },
    }
