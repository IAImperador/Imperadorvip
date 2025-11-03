from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .routers import health, analyze

app = FastAPI(title="IA do Imperador", version="4.0")

origins = ["*"] if settings.ALLOWED_ORIGINS in ["*", "", None] else [o.strip() for o in settings.ALLOWED_ORIGINS.split(",")]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

app.include_router(health.router)
app.include_router(analyze.router)
