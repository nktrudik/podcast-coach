from fastapi import APIRouter

from app.api.routes.admin import router as admin_router
from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router
from app.api.routes.videos import router as videos_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(videos_router, tags=["videos"])
api_router.include_router(chat_router, tags=["chat"])
api_router.include_router(admin_router, tags=["admin"])
