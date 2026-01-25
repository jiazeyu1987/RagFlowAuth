from fastapi import APIRouter

router = APIRouter()

from .routes.upload import router as upload_router  # noqa: E402
from .routes.documents import router as documents_router  # noqa: E402
from .routes.files import router as files_router  # noqa: E402
from .routes.admin import router as admin_router  # noqa: E402

router.include_router(upload_router)
router.include_router(documents_router)
router.include_router(files_router)
router.include_router(admin_router)

