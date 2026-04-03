from fastapi import APIRouter

router = APIRouter()

from .routes.challenge import router as challenge_router  # noqa: E402
from .routes.manage import router as manage_router  # noqa: E402

router.include_router(challenge_router)
router.include_router(manage_router)
