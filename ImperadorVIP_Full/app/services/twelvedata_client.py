
from __future__ import annotations
import httpx, pandas as pd

BASE = "https://api.twelvedata.com"

async def fetch_timeseries(symbol: str, interval: str, apikey: str, outputsize: int = 200) -> pd.DataFrame:
    url = f"{BASE}/time_series"
    params = {
        "symbol": symbol,
        "interval": interval.lower(),
        "outputsize": outputsize,
        "apikey": apikey,
        "dp": 6,
        "format": "JSON"
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
    if "values" not in data:
        raise RuntimeError(f"TwelveData error: {data.get('message', 'unknown')}")
    df = pd.DataFrame(data["values"]).rename(columns=str.lower)
    for col in ["open","high","low","close","volume"]:
        if col in df.columns: df[col] = df[col].astype(float)
        else: df[col] = 0.0
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    return df[["datetime","open","high","low","close","volume"]]
