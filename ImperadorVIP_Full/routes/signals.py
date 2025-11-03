
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal
from app.core.config import settings
from app.services.twelvedata_client import fetch_timeseries
from app.services.analysis import last_signal

router = APIRouter(prefix="/signals", tags=["signals"])

class ManualRequest(BaseModel):
    broker: str
    symbol: str
    timeframe: Literal["M1","M5","M15","M30","H1"] = "M5"
    market_type: Literal["otc","open"] = "open"
    candles: int = 200

@router.get("/config")
async def get_config():
    return {
        "allow_brokers": [
            "Quotex","Polarium","IQ Option","Deriv","Bullex","Avalon",
            "Okbroker","Orkatrader","Casa Trader"
        ],
        "timeframes": ["M1","M5","M15","M30","H1"]
    }

@router.post("/manual")
async def manual(req: ManualRequest):
    if not settings.TWELVEDATA_KEY:
        raise HTTPException(status_code=500, detail="TWELVEDATA_KEY não configurada")
    df = await fetch_timeseries(req.symbol, req.timeframe, settings.TWELVEDATA_KEY, req.candles)
    result = last_signal(df, req.market_type)
    result.update({"symbol": req.symbol, "timeframe": req.timeframe, "mode": "manual"})
    return result

class AutoRequest(BaseModel):
    broker: str
    symbol: str
    timeframe: Literal["M1","M5","M15","M30","H1"] = "M5"
    market_type: Literal["otc","open"] = "open"
    candles: int = 200

@router.post("/auto")
async def auto(req: AutoRequest):
    if not settings.TWELVEDATA_KEY:
        raise HTTPException(status_code=500, detail="TWELVEDATA_KEY não configurada")
    df = await fetch_timeseries(req.symbol, req.timeframe, settings.TWELVEDATA_KEY, req.candles)
    result = last_signal(df, req.market_type)
    result.update({"symbol": req.symbol, "timeframe": req.timeframe, "mode": "auto"})
    return result
