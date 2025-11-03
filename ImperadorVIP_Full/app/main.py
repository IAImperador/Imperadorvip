
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from routes.healthcheck import router as health_router
from routes.signals import router as signals_router

app = FastAPI(title="Imperador VIP API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.ALLOW_METHODS,
    allow_headers=settings.ALLOW_HEADERS,
)

app.include_router(health_router)
app.include_router(signals_router)

@app.get("/")
async def root():
    return {"name": "Imperador VIP API", "status": "running"}
