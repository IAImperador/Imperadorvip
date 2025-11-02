from fastapi import APIRouter, HTTPException, Query
from typing import Literal
from app.core.config import settings
from app.services.datafeed import fetch_ohlc
from app.services.market import effective_market
from app.indicators.ta import confluence_score
from app.utils.symbols import FOREX_PAIRS

router = APIRouter()

@router.get("/symbols")
async def symbols():
    return {"symbols": FOREX_PAIRS}

@router.get("/signal/next")
async def next_signal(
    api_key: str = Query(..., description="Chave do painel (API_KEY)"),
    symbol: str = Query("EURUSD"),
    timeframe: str = Query("5min"),
    market: Literal["auto","open","otc"] = Query("auto"),
    min_conf: int = Query(90, ge=0, le=100)
):
    if api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="API_KEY inválida")
    mode = effective_market(market)
    df = await fetch_ohlc(symbol, timeframe, settings.TWELVEDATA_KEY, market=mode, limit=200)
    if df.empty or len(df) < 50:
        raise HTTPException(status_code=400, detail="Dados insuficientes")
    conf = confluence_score(df)
    action = "CALL" if "EMA9>EMA21 (tendência alta)" in conf["items"] else "PUT"
    result = {
        "symbol": symbol,
        "timeframe": timeframe,
        "market": mode,
        "confidence": conf["score"],
        "reasons": conf["items"],
        "rsi": conf["rsi"],
        "action": action,
        "entry": str(df.iloc[-1]["time"]),
        "expiry_candles": 1,
        "ok": conf["score"] >= min_conf
    }
    return result
