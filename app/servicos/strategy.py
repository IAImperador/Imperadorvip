import numpy as np
import pandas as pd

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def confluence_signal(df: pd.DataFrame) -> dict:
    close = df["close"]
    ema9 = ema(close, 9)
    ema21 = ema(close, 21)
    r = rsi(close, 14)
    body = (df["close"] - df["open"]).abs()
    body_mean = body.rolling(20).mean()

    last = len(df) - 1
    trend_up = ema9.iloc[last] > ema21.iloc[last]
    trend_down = ema9.iloc[last] < ema21.iloc[last]
    mom_up = r.iloc[last] > 55
    mom_down = r.iloc[last] < 45
    strong_body = body.iloc[last] > (body_mean.iloc[last] or 0)

    score = 50
    if trend_up: score += 15
    if trend_down: score -= 15
    if mom_up: score += 20
    if mom_down: score -= 20
    if strong_body: score += 10

    direction = "CALL" if score >= 50 else "PUT"
    score = max(0, min(100, round(score, 2)))
    return {"direction": direction, "score": score}
