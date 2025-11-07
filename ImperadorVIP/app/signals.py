from datetime import datetime, timezone
from .config import settings
from .state import state
from .indicators import build_signal

async def generate_signal_once(symbol: str, timeframe: str, min_confidence: int = 90):
    res = build_signal(symbol=symbol, interval=timeframe, api_key=settings.twelvedata_key, min_conf=min_confidence)
    payload = {
        "ok": res["ok"],
        "symbol": symbol,
        "timeframe": timeframe,
        "market": state.market,
        "mode": state.mode,
        "side": res["side"],
        "confidence": res["confidence"],
        "confluences": res["confluences"],
        "entry_time": datetime.now(timezone.utc).isoformat(),
        "message": "Análise OK" if res["ok"] else "Confluência insuficiente"
    }
    state.last_signal = payload
    state.updated_at = datetime.now(timezone.utc).isoformat()
    return payload
