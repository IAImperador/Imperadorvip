from fastapi import APIRouter
import datetime

router = APIRouter()

@router.get("/")
async def status():
    return {
        "status": "ok",
        "time": datetime.datetime.utcnow().isoformat(),
        "service": "ImperadorVIP Health Monitor"
    }
