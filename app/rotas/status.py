from fastapi import APIRouter
from app.core.config import settings
from app.main import autorunner

router = APIRouter(tags=["Status"])

@router.get("/status")
def api_status():
    return {
        "service": "ImperadorVIP Signals API",
        "env": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "auto_enabled": autorunner.enabled
    }
