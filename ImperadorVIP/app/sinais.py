from __future__ import annotations
import httpx, pandas as pd
from datetime import datetime, timezone

TWELVE_URL = "https://api.twelvedata.com/time_series"

def _tf_seconds(tf: str) -> int:
    return {"1":60,"3":180,"5":300,"15":900}.get(str(tf), 300)

async def fetch_serie(symbol: str, tf: str, key: str) -> pd.DataFrame:
    interval = {"1":"1min","3":"3min","5":"5min","15":"15min"}[str(tf)]
    params = {"symbol": symbol, "interval": interval, "apikey": key, "outputsize": 150}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(TWELVE_URL, params=params)
        r.raise_for_status()
        data = r.json()
    if "values" not in data:
        raise RuntimeError(f"Sem 'values' para {symbol}: {data}")
    df = pd.DataFrame(data["values"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    for col in ["open","high","low","close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.sort_values("datetime").set_index("datetime")
    return df[["open","high","low","close"]].dropna()

from .confluencias import score_confluencia

async def gerar_sinal(symbol: str, tf: str, key: str, market_mode: str) -> dict:
    df = await fetch_serie(symbol, tf, key)
    conf = score_confluencia(df)
    exp_seconds = _tf_seconds(tf)
    now = datetime.now(timezone.utc).isoformat()
    return {"symbol": symbol, "timeframe": tf, "market_mode": market_mode, "confluencia": conf, "entrada_em": exp_seconds, "gerado_em_utc": now}
