from fastapi import APIRouter

from .routes import datasets, documents, downloads

router = APIRouter()

router.include_router(datasets.router)
router.include_router(documents.router)
router.include_router(downloads.router)

