from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.scheduler import AutoRunner
from app.rotas import signals, status as status_routes
from app.servicos.market_data import fetch_series
from app.servicos.strategy import confluence_signal
import asyncio, datetime

app = FastAPI(title="ImperadorVIP Signals API", version="5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

autorunner = AutoRunner(interval_seconds=300)

def auto_job():
    try:
        df = fetch_series("EUR/JPY", interval="5min", outputsize=120)
        sig = confluence_signal(df)
        print(f"[AUTO] {datetime.datetime.utcnow().isoformat()} -> EUR/JPY {sig}")
    except Exception as e:
        print(f"[AUTO] erro: {e}")

@app.get("/")
def root():
    return {"status": "ok", "service": "ImperadorVIP Signals API"}

@app.post("/auto/toggle")
def toggle_auto(x_api_key: str = Header(default="")):
    if x_api_key != settings.API_KEY:
        raise HTTPException(401, "unauthorized")
    if autorunner.enabled:
        autorunner.stop()
        return {"status": "ok", "auto_enabled": False}
    autorunner.start(auto_job)
    return {"status": "ok", "auto_enabled": True}

app.include_router(signals.router)
app.include_router(status_routes.router)
