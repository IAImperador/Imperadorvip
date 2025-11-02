import httpx, pandas as pd
from typing import Literal
BASE = "https://api.twelvedata.com"
async def fetch_ohlc(symbol: str, interval: str, apikey: str, market: Literal["open","otc"]="open", limit: int = 150) -> pd.DataFrame:
    params = {"symbol": symbol, "interval": interval, "apikey": apikey, "outputsize": limit, "dp": 5, "timezone": "UTC"}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(f"{BASE}/time_series", params=params)
        r.raise_for_status()
        js = r.json()
        if "values" not in js: raise RuntimeError(f"Erro TwelveData: {js}")
        df = pd.DataFrame(js["values"]).rename(columns={"datetime":"time"})
        for c in ["open","high","low","close"]: df[c]=df[c].astype(float)
        df["time"]=pd.to_datetime(df["time"], utc=True)
        df=df.sort_values("time").reset_index(drop=True)
        return df
