import os
from pydantic import BaseModel
class Settings(BaseModel):
    PORT: int = int(os.getenv("PORT","8080"))
    API_KEY: str = os.getenv("API_KEY","imperadorvip-secure-key-2025")
    TWELVEDATA_KEY: str = os.getenv("TWELVEDATA_KEY","")
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS","*")
settings = Settings()
