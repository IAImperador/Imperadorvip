from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
from .config import settings
from .state import state
from .schemas import ToggleRequest, ModeRequest, MarketRequest, SignalRequest, SignalResult
from .scheduler import start_scheduler
from .signals import generate_signal_once

app = FastAPI(title="ImperadorVIP – Sinais Inteligentes", version="5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _auth(api_key: str):
    if api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="API_KEY inválida")

@app.get("/")
def root():
    return {"status":"ok","service":"ImperadorVIP Signals API","time":datetime.now(timezone.utc).isoformat()}

@app.get("/health")
def health():
    return {"ok": True, "env": settings.environment, "debug": settings.debug}

@app.get("/status")
def status():
    return {"enabled":state.enabled,"mode":state.mode,"market":state.market,"last_signal":state.last_signal,"updated_at":state.updated_at}

@app.post("/toggle")
def toggle(req: ToggleRequest):
    _auth(req.api_key)
    state.enabled = not state.enabled
    state.updated_at = datetime.now(timezone.utc).isoformat()
    if state.enabled and state.mode == "auto":
        start_scheduler()
    return {"enabled": state.enabled}

@app.post("/mode")
def set_mode(req: ModeRequest):
    _auth(req.api_key)
    state.mode = req.mode
    state.updated_at = datetime.now(timezone.utc).isoformat()
    if state.mode == "auto" and state.enabled:
        start_scheduler()
    return {"mode": state.mode}

@app.post("/market")
def set_market(req: MarketRequest):
    _auth(req.api_key)
    state.market = req.market
    state.updated_at = datetime.now(timezone.utc).isoformat()
    return {"market": state.market}

@app.post("/signal", response_model=SignalResult)
async def signal(req: SignalRequest):
    _auth(req.api_key)
    result = await generate_signal_once(symbol=req.symbol, timeframe=req.timeframe, min_confidence=req.min_confidence)
    return result
