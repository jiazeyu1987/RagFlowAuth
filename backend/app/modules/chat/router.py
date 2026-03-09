from fastapi import APIRouter

from .routes_chats import router as chats_router
from .routes_completions import router as completions_router
from .routes_sessions import router as sessions_router


router = APIRouter()
router.include_router(chats_router)
router.include_router(sessions_router)
router.include_router(completions_router)
