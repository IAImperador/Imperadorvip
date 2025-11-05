import os
import httpx
import numpy as np
import pandas as pd
from fastapi import FastAPI, Body, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime, timezone

API_KEY = os.getenv("API_KEY", "imperadorvip-secure-key-2025")
TWELVE_KEY = os.getenv("TWELVEDATA_KEY", "")
DEFAULT_PORT = int(os.getenv("PORT", "8080"))

app = FastAPI(title="ImperadorVIP API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TF_MAP = {
    "M1": "1min", "M2": "2min", "M3": "3min", "M5": "5min",
    "M10": "10min", "M15": "15min", "M30": "30min", "H1": "1h",
}

def _auth_or_401(x_api_key: str | None):
    if (x_api_key or "").strip() != API_KEY:
        raise HTTPException(status_code=401, detail="x-api-key inválida")

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.fillna(50)

def macd(series: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k=14, d=3):
    lowest_low = low.rolling(k).min()
    highest_high = high.rolling(k).max()
    k_percent = 100 * (close - lowest_low) / (highest_high - lowest_low)
    d_percent = k_percent.rolling(d).mean()
    return k_percent.fillna(50), d_percent.fillna(50)

def bollinger(close: pd.Series, period=20, std=2.0):
    ma = close.rolling(period).mean()
    dev = close.rolling(period).std(ddof=0)
    upper = ma + std * dev
    lower = ma - std * dev
    return ma, upper, lower

def is_bullish_engulfing(df: pd.DataFrame) -> bool:
    if len(df) < 2: return False
    prev = df.iloc[-2]; cur = df.iloc[-1]
    return (prev["close"] < prev["open"]) and (cur["close"] > cur["open"]) and \
           (cur["open"] <= prev["close"]) and (cur["close"] >= prev["open"])

def is_bearish_engulfing(df: pd.DataFrame) -> bool:
    if len(df) < 2: return False
    prev = df.iloc[-2]; cur = df.iloc[-1]
    return (prev["close"] > prev["open"]) and (cur["close"] < cur["open"]) and \
           (cur["open"] >= prev["close"]) and (cur["close"] <= prev["open"])

def is_hammer(df: pd.DataFrame) -> bool:
    if len(df) < 1: return False
    c = df.iloc[-1]
    body = abs(c["close"] - c["open"])
    lower_wick = min(c["open"], c["close"]) - c["low"]
    upper_wick = c["high"] - max(c["open"], c["close"])
    return (lower_wick > body * 2) and (upper_wick < body)

def get_twelvedata_candles(symbol: str, interval: str, bars: int = 200) -> pd.DataFrame:
    if not TWELVE_KEY:
        raise HTTPException(status_code=500, detail="TWELVEDATA_KEY não configurada")
    url = "https://api.twelvedata.com/time_series"
    params = {"symbol": symbol, "interval": interval, "outputsize": bars,
              "format": "JSON", "apikey": TWELVE_KEY, "timezone": "UTC", "order": "ASC"}
    with httpx.Client(timeout=30) as client:
        r = client.get(url, params=params)
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"TwelveData HTTP {r.status_code}")
        j = r.json()
        if "values" not in j:
            raise HTTPException(status_code=400, detail=f"Resposta inválida TwelveData: {j}")
    rows = [{
        "time": pd.to_datetime(v["datetime"], utc=True),
        "open": float(v["open"]), "high": float(v["high"]),
        "low": float(v["low"]), "close": float(v["close"])
    } for v in j["values"]]
    return pd.DataFrame(rows).sort_values("time").reset_index(drop=True)

def compute_confluences(df: pd.DataFrame):
    close, high, low = df["close"], df["high"], df["low"]
    ema9, ema21 = ema(close, 9), ema(close, 21)
    rsi14 = rsi(close, 14)
    macd_line, signal_line, hist = macd(close)
    k, d = stochastic(high, low, close, 14, 3)
    ma20, bb_up, bb_lo = bollinger(close, 20, 2.0)
    latest = len(df) - 1

    score_long = score_short = 0
    reasons_long, reasons_short = [], []

    if ema9.iloc[latest] > ema21.iloc[latest]:
        score_long += 1; reasons_long.append("Tendência de alta (EMA9>EMA21)")
    elif ema9.iloc[latest] < ema21.iloc[latest]:
        score_short += 1; reasons_short.append("Tendência de baixa (EMA9<EMA21)")

    if rsi14.iloc[latest] < 35:
        score_long += 1; reasons_long.append("RSI sobrevendido (<35)")
    if rsi14.iloc[latest] > 65:
        score_short += 1; reasons_short.append("RSI sobrecomprado (>65)")

    if hist.iloc[latest] > 0 and macd_line.iloc[latest] > signal_line.iloc[latest]:
        score_long += 1; reasons_long.append("MACD positivo")
    if hist.iloc[latest] < 0 and macd_line.iloc[latest] < signal_line.iloc[latest]:
        score_short += 1; reasons_short.append("MACD negativo")

    if k.iloc[latest] > d.iloc[latest] and k.iloc[latest] < 80:
        score_long += 1; reasons_long.append("Estocástico cruzado p/ cima")
    if k.iloc[latest] < d.iloc[latest] and k.iloc[latest] > 20:
        score_short += 1; reasons_short.append("Estocástico cruzado p/ baixo")

    c = close.iloc[latest]
    if c <= bb_lo.iloc[latest]:
        score_long += 1; reasons_long.append("Toque na banda inferior")
    if c >= bb_up.iloc[latest]:
        score_short += 1; reasons_short.append("Toque na banda superior")

    if is_bullish_engulfing(df) or is_hammer(df):
        score_long += 1; reasons_long.append("Padrão altista (Engolfo/Hammer)")
    if is_bearish_engulfing(df):
        score_short += 1; reasons_short.append("Padrão baixista (Engolfo)")

    if score_long > score_short:
        direction, reasons, confluences = "CALL", reasons_long, score_long
    elif score_short > score_long:
        direction, reasons, confluences = "PUT", reasons_short, score_short
    else:
        direction, reasons, confluences = "NEUTRO", ["Sem direção clara"], score_long

    max_confs = 6
    base_conf = min(confluences / max_confs, 1.0)
    vol = close.rolling(20).std(ddof=0).iloc[latest] / max(close.iloc[latest], 1e-9)
    vol_adj = 1.0 - min(vol * 5, 0.4)
    confidence = round(float(max(0.0, min(1.0, base_conf * vol_adj))), 3)

    return {"direction": direction, "confluences": confluences,
            "confidence": confidence, "reasons": reasons}

class SignalRequest(BaseModel):
    broker: str
    symbol: str
    timeframe: str
    market: str
    candles: int = 200
    min_confluences: int = 5
    min_confidence: float = 0.9
    risk_mode: str = "normal"

class SignalResponse(BaseModel):
    ok: bool
    entry: dict | None
    analysis: dict

@app.get("/health")
def health():
    return {"ok": True, "time": datetime.now(timezone.utc).isoformat()}

@app.get("/config")
def config(x_api_key: str | None = Header(default=None, alias="x-api-key")):
    _auth_or_401(x_api_key)
    return {
        "supported_timeframes": list(TF_MAP.keys()),
        "min_confluences_default": 5,
        "min_confidence_default": 0.9,
        "auto_interval_minutes": 5,
        "notes": "OTC via flag; leitura usa mesma feed até você plugar OTC nativa."
    }

@app.post("/sinal/manual", response_model=SignalResponse)
def sinal_manual(payload: SignalRequest, x_api_key: str | None = Header(default=None, alias="x-api-key")):
    _auth_or_401(x_api_key)
    tf = TF_MAP.get(payload.timeframe.upper())
    if not tf: raise HTTPException(status_code=400, detail="timeframe inválido")

    df = get_twelvedata_candles(payload.symbol.replace(" ", ""), tf, bars=max(120, payload.candles))
    if len(df) < 60: raise HTTPException(status_code=400, detail="Poucos candles retornados")

    result = compute_confluences(df)
    ok = (result["confluences"] >= payload.min_confluences) and \
         (result["confidence"] >= payload.min_confidence) and \
         (result["direction"] in ["CALL", "PUT"])

    entry = None
    if ok:
        entry = {
            "symbol": payload.symbol,
            "broker": payload.broker,
            "market": payload.market,
            "timeframe": payload.timeframe,
            "direction": result["direction"],
            "valid_for_minutes": 5 if payload.timeframe.upper().startswith("M") else 60,
            "suggested_expiration": payload.timeframe.upper(),
        }
    return {"ok": ok, "entry": entry, "analysis": result}

@app.post("/sinal/auto", response_model=SignalResponse)
def sinal_auto(payload: SignalRequest, x_api_key: str | None = Header(default=None, alias="x-api-key")):
    return sinal_manual(payload, x_api_key)
