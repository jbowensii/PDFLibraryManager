"""API routers and endpoints."""

from fastapi import APIRouter

router = APIRouter()

# Import and include all routers
from .auth import router as auth_router
from .books import router as books_router
from .collections import router as collections_router
from .duplicates import router as duplicates_router
from .search import router as search_router
from .admin import router as admin_router
from .library import router as library_router

router.include_router(auth_router, prefix='/auth', tags=['Authentication'])
router.include_router(books_router, prefix='/books', tags=['Books'])
router.include_router(collections_router, prefix='/collections', tags=['Collections'])
router.include_router(duplicates_router, prefix='/duplicates', tags=['Duplicates'])
router.include_router(search_router, prefix='/search', tags=['Search'])
router.include_router(admin_router, prefix='/admin', tags=['Admin'])
router.include_router(library_router, prefix='/library', tags=['Library'])

__all__ = ['router']
