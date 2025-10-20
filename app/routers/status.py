from fastapi import APIRouter
import os

router = APIRouter(prefix="/status", tags=["Status"])

@router.get("/")
async def status():
    brokers = []
    if os.getenv("ENABLE_DERIV") == "True":
        brokers.append("Deriv")
    if os.getenv("ENABLE_QUOTEX") == "True":
        brokers.append("Quotex")
    if os.getenv("ENABLE_IQOPTION") == "True":
        brokers.append("IQ Option")
    if os.getenv("ENABLE_BINOMO") == "True":
        brokers.append("Binomo")
    if os.getenv("ENABLE_POCKETOPTION") == "True":
        brokers.append("PocketOption")
    if os.getenv("ENABLE_OLYMPTRADE") == "True":
        brokers.append("OlympTrade")

    return {
        "status": "online",
        "app": os.getenv("APP_NAME", "ImperadorVIP"),
        "brokers_enabled": brokers,
        "message": "IA ImperadorVIP ativo e rodando com sucesso."
    }
