from fastapi import APIRouter
from app.core.config import settings
router = APIRouter()
@router.get("/config")
async def get_config():
    return {"port": settings.PORT, "has_twelvedata": bool(settings.TWELVEDATA_KEY)}
