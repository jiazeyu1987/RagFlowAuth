from fastapi import APIRouter

router = APIRouter()

from .routes.conflict import router as conflict_router  # noqa: E402
from .routes.approve import router as approve_router  # noqa: E402
from .routes.overwrite import router as overwrite_router  # noqa: E402
from .routes.reject import router as reject_router  # noqa: E402

router.include_router(conflict_router)
router.include_router(approve_router)
router.include_router(overwrite_router)
router.include_router(reject_router)

