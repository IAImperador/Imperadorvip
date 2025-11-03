
from __future__ import annotations
import pandas as pd
from typing import Literal, Dict, Any
from .twelvedata_client import fetch_timeseries
from app.core.indicators import rsi, macd, ema, sma, bollinger, vwap
from app.utils import patterns as pat

def last_signal(df: pd.DataFrame, market_type: Literal["otc","open"]) -> Dict[str, Any]:
    df = df.copy()
    df["ema20"] = ema(df["close"], 20)
    df["ema50"] = ema(df["close"], 50)
    df["sma200"] = sma(df["close"], 200)
    df["rsi14"] = rsi(df["close"], 14)
    macd_line, signal_line, hist = macd(df["close"])
    df["macd"], df["macd_signal"], df["macd_hist"] = macd_line, signal_line, hist
    up, mid, low = bollinger(df["close"], 20, 2.0)
    df["bb_upper"], df["bb_mid"], df["bb_lower"] = up, mid, low
    if (df["volume"] > 0).any():
        df["vwap"] = vwap(df["high"], df["low"], df["close"], df["volume"])
    else:
        df["vwap"] = df["close"]

    df["bull_eng"] = pat.is_bullish_engulfing(df).astype(int)
    df["bear_eng"] = pat.is_bearish_engulfing(df).astype(int)
    df["hammer"] = pat.is_hammer(df).astype(int)
    df["shooting"] = pat.is_shooting_star(df).astype(int)

    last = df.iloc[-1]
    prev = df.iloc[-2]

    confluences = []

    if last["ema20"] > last["ema50"]:
        confluences.append(("trend_up", +1))
    elif last["ema20"] < last["ema50"]:
        confluences.append(("trend_down", -1))

    if last["rsi14"] <= 30: confluences.append(("rsi_oversold", +1))
    if last["rsi14"] >= 70: confluences.append(("rsi_overbought", -1))

    if (prev["macd"] < prev["macd_signal"]) and (last["macd"] > last["macd_signal"]):
        confluences.append(("macd_bull_cross", +1))
    if (prev["macd"] > prev["macd_signal"]) and (last["macd"] < last["macd_signal"]):
        confluences.append(("macd_bear_cross", -1))
    if last["macd_hist"] > 0: confluences.append(("macd_hist_up", +0.5))
    if last["macd_hist"] < 0: confluences.append(("macd_hist_down", -0.5))

    if last["close"] < last["bb_lower"]: confluences.append(("bb_bounce_up", +1))
    if last["close"] > last["bb_upper"]: confluences.append(("bb_bounce_down", -1))

    if last["close"] > last["vwap"]: confluences.append(("above_vwap", +0.5))
    else: confluences.append(("below_vwap", -0.5))

    if last["bull_eng"] == 1: confluences.append(("bullish_engulfing", +1))
    if last["bear_eng"] == 1: confluences.append(("bearish_engulfing", -1))
    if last["hammer"] == 1: confluences.append(("hammer", +0.5))
    if last["shooting"] == 1: confluences.append(("shooting_star", -0.5))

    score = sum(w for _, w in confluences)
    conf = max(0.0, min(100.0, 50 + score * 10))

    direction = "CALL" if conf >= 50 and score >= 0 else "PUT"
    rationale = [name for name, _ in confluences]

    return {
        "direction": direction,
        "confidence": round(conf, 2),
        "price": float(last["close"]),
        "time": str(last["datetime"]),
        "confluences": rationale,
        "market_type": market_type
    }
