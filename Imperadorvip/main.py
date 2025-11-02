from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.health import router as health_router
from app.routes.config import router as config_router
from app.routes.signal import router as signal_router

app = FastAPI(title="ImperadorVIP API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router, tags=["system"])
app.include_router(config_router, tags=["system"])
app.include_router(signal_router, tags=["signals"])
@app.get("/")
async def root():
    return {"name":"ImperadorVIP API","status":"ok"}
