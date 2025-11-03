import httpx, pandas as pd
from . import indicators
from ..config import settings
BASE_URL = "https://api.twelvedata.com/time_series"
def fetch_candles(symbol: str, interval: str, limit: int) -> pd.DataFrame:
    params = {
        "symbol": symbol.replace("/", ""),
        "interval": interval.lower(),
        "apikey": settings.TWELVEDATA_KEY,
        "outputsize": limit,
        "format": "JSON",
        "dp": 6,
        "timezone": "UTC",
        "order": "ASC"
    }
    with httpx.Client(timeout=20) as client:
        r = client.get(BASE_URL, params=params)
        r.raise_for_status()
        data = r.json()
    if "values" not in data:
        raise RuntimeError(f"TwelveData response: {data}")
    df = pd.DataFrame(data["values"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    for c in ["open","high","low","close"]:
        df[c] = pd.to_numeric(df[c])
    return df.sort_values("datetime").reset_index(drop=True)
def compute_confluence(df: pd.DataFrame):
    sigs = []
    rsi = indicators.rsi(df["close"], 14)
    last_rsi = rsi.iloc[-1]
    if last_rsi <= 30: sigs.append("RSI sobrevendido (CALL)")
    elif last_rsi >= 70: sigs.append("RSI sobrecomprado (PUT)")
    ema9 = indicators.ema(df["close"], 9); ema21 = indicators.ema(df["close"], 21)
    if ema9.iloc[-1] > ema21.iloc[-1] and ema9.iloc[-2] <= ema21.iloc[-2]: sigs.append("Cruz EMA9>EMA21 (CALL)")
    if ema9.iloc[-1] < ema21.iloc[-1] and ema9.iloc[-2] >= ema21.iloc[-2]: sigs.append("Cruz EMA9<EMA21 (PUT)")
    up, mid, low = indicators.bbands(df["close"], 20, 2)
    last_close = df["close"].iloc[-1]
    if last_close <= low.iloc[-1]: sigs.append("Bollinger inferior (CALL)")
    if last_close >= up.iloc[-1]: sigs.append("Bollinger superior (PUT)")
    body = abs(df["close"].iloc[-1]-df["open"].iloc[-1])
    rang = df["high"].iloc[-1]-df["low"].iloc[-1]
    if rang>0 and body/rang<0.25: sigs.append("Candle indecisão (reversão)")
    support = df["low"].tail(20).min(); resist = df["high"].tail(20).max()
    if last_close <= support*1.002: sigs.append("Suporte (CALL)")
    if last_close >= resist*0.998: sigs.append("Resistência (PUT)")
    score = min(1.0, len(sigs)/8.0)
    upv = sum("CALL" in s for s in sigs); dnv = sum("PUT" in s for s in sigs)
    direction = "CALL" if upv>dnv else ("PUT" if dnv>upv else "NEUTRAL")
    summary = f"Confluências={len(sigs)} | RSI={last_rsi:.1f} | Dir={direction}"
    return sigs, score, summary, direction
