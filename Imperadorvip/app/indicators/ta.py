import numpy as np
import pandas as pd

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1*delta.clip(upper=0)
    ma_up = up.ewm(com=period-1, adjust=False).mean()
    ma_down = down.ewm(com=period-1, adjust=False).mean()
    rs = ma_up / (ma_down.replace(0, np.nan))
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def bollinger(series: pd.Series, period: int = 20, std_mult: float = 2.0):
    ma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = ma + std_mult * std
    lower = ma - std_mult * std
    return ma, upper, lower

def candle_patterns(df: pd.DataFrame):
    out = {
        "pinbar_bull": False,
        "pinbar_bear": False,
        "engolfo_bull": False,
        "engolfo_bear": False,
        "martelo": False,
        "estrela_cadente": False,
    }
    if len(df) < 2:
        return out
    c1 = df.iloc[-2]; c2 = df.iloc[-1]
    body2 = abs(c2.close - c2.open)
    range2 = c2.high - c2.low
    upper_wick2 = c2.high - max(c2.close, c2.open)
    lower_wick2 = min(c2.close, c2.open) - c2.low
    if range2 > 0:
        if upper_wick2 > 2*body2 and lower_wick2 < body2:
            out["pinbar_bear"] = True
        if lower_wick2 > 2*body2 and upper_wick2 < body2:
            out["pinbar_bull"] = True
    if (c2.close > c2.open) and (c1.close < c1.open) and (c2.close >= c1.open) and (c2.open <= c1.close):
        out["engolfo_bull"] = True
    if (c2.close < c2.open) and (c1.close > c1.open) and (c2.close <= c1.open) and (c2.open >= c1.close):
        out["engolfo_bear"] = True
    if lower_wick2 > 2*body2 and upper_wick2 < body2:
        out["martelo"] = True
    if upper_wick2 > 2*body2 and lower_wick2 < body2:
        out["estrela_cadente"] = True
    return out

def confluence_score(df: pd.DataFrame) -> dict:
    score_items = []
    close = df["close"]
    r = rsi(close, 14)
    last_rsi = float(r.iloc[-1])
    if last_rsi < 30:
        score_items.append(("RSI<30 (sobrevendido)", +1))
    elif last_rsi > 70:
        score_items.append(("RSI>70 (sobrecomprado)", +1))
    ema9 = ema(close, 9); ema21 = ema(close, 21)
    if ema9.iloc[-1] > ema21.iloc[-1]:
        score_items.append(("EMA9>EMA21 (tendência alta)", +1))
    else:
        score_items.append(("EMA9<EMA21 (tendência baixa)", +1))
    ma, up, lo = bollinger(close, 20, 2.0)
    if close.iloc[-1] <= lo.iloc[-1]:
        score_items.append(("Toque Banda Inferior", +1))
    if close.iloc[-1] >= up.iloc[-1]:
        score_items.append(("Toque Banda Superior", +1))
    pads = candle_patterns(df)
    for k,v in pads.items():
        if v: score_items.append((k.replace("_"," ").title(), +1))
    total = sum(w for _,w in score_items)
    conf = int((total/8.0)*100); conf = max(0, min(100, conf))
    return {"score": conf, "items": [n for n,_ in score_items], "rsi": last_rsi}
