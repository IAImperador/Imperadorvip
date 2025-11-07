from pydantic import BaseModel
from typing import Literal
import os

class Settings(BaseModel):
    port: int = int(os.getenv("PORT","8080"))
    api_key: str = os.getenv("API_KEY","imperadorvip-secure-key-2025")
    twelvedata_key: str = os.getenv("TWELVEDATA_KEY","")
    environment: Literal["production","development"] = os.getenv("ENVIRONMENT","production")
    debug: bool = os.getenv("DEBUG","false").lower() == "true"

settings = Settings()
