import requests, pandas as pd
from app.core.config import settings

BASE_URL = "https://api.twelvedata.com/time_series"

def fetch_series(symbol: str, interval: str = "5min", outputsize: int = 120) -> pd.DataFrame:
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": settings.TWELVEDATA_KEY,
        "format": "JSON"
    }
    r = requests.get(BASE_URL, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    if "values" not in data:
        raise ValueError(f"Sem dados para {symbol}: {data}")
    df = pd.DataFrame(data["values"])
    df = df.rename(columns={"datetime":"time","open":"open","high":"high","low":"low","close":"close"})
    for col in ["open","high","low","close"]:
        df[col] = df[col].astype(float)
    df["time"] = pd.to_datetime(df["time"])
    df = df.sort_values("time").reset_index(drop=True)
    return df
