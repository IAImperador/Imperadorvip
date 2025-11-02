import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    PORT: int = int(os.getenv("PORT", "8080"))
    API_KEY: str = os.getenv("API_KEY", "imperadorvip-secure-key-2025")
    TWELVEDATA_KEY: str = os.getenv("TWELVEDATA_KEY", "")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

settings = Settings()
