from fastapi import APIRouter
from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
    }
