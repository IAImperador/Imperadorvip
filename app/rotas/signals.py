from fastapi import APIRouter, Query
from app.servicos.market_data import fetch_series
from app.servicos.strategy import confluence_signal
from datetime import datetime

router = APIRouter(prefix="/signal", tags=["Signals"])

OTC_DEFAULTS = ["EUR/USD","USD/JPY","GBP/USD","AUD/CAD","EUR/CHF","NZD/JPY"]
OPEN_DEFAULTS = ["EUR/JPY","USD/CHF","GBP/JPY","AUD/USD","CAD/JPY","EUR/CAD"]

@router.get("/live")
def live_signal(market: str = Query("aberto", pattern="^(otc|aberto)$"), symbol: str = ""):
    if not symbol:
        symbol = (OTC_DEFAULTS if market == "otc" else OPEN_DEFAULTS)[0]
    df = fetch_series(symbol, interval="5min", outputsize=120)
    sig = confluence_signal(df)
    now = datetime.utcnow().isoformat()
    return {
        "status": "ok",
        "generated_at": now,
        "market": market,
        "symbol": symbol,
        "signal": sig["direction"],
        "confidence": sig["score"]
    }
