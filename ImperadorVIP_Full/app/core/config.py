
from pydantic import BaseModel
import os

class Settings(BaseModel):
    PORT: int = int(os.getenv("PORT", "8080"))
    API_KEY: str = os.getenv("API_KEY", "imperadorvip-secure-key-2025")
    TWELVEDATA_KEY: str = os.getenv("TWELVEDATA_KEY", "")
    ALLOW_ORIGINS: list[str] = ["*"]
    ALLOW_METHODS: list[str] = ["*"]
    ALLOW_HEADERS: list[str] = ["*"]

settings = Settings()
