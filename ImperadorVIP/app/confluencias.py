from __future__ import annotations
import pandas as pd
from .indicadores import ema, rsi, macd, bbands, detect_candles

def score_confluencia(df: pd.DataFrame) -> dict:
    df = df.copy().dropna().tail(100)
    if len(df) < 30:
        return { "score": 0, "direcao": "neutro", "explicacao": ["dados insuficientes"] }
    close = df['close']
    ema20 = ema(close, 20)
    r = rsi(close, 14)
    macd_line, macd_sig, macd_hist = macd(close)
    bb_h, bb_l, _ = bbands(close, 20)
    patt = detect_candles(df)

    s_buy = s_sell = 0
    notes = []
    if r.iloc[-1] < 30: s_buy += 2; notes.append("RSI < 30")
    elif r.iloc[-1] > 70: s_sell += 2; notes.append("RSI > 70")
    if close.iloc[-1] > ema20.iloc[-1] and close.iloc[-2] <= ema20.iloc[-2]: s_buy += 2; notes.append("Cruzou acima EMA20")
    elif close.iloc[-1] < ema20.iloc[-1] and close.iloc[-2] >= ema20.iloc[-2]: s_sell += 2; notes.append("Cruzou abaixo EMA20")
    if (macd_hist.iloc[-1] > 0) and (macd_line.iloc[-1] > macd_sig.iloc[-1]): s_buy += 2; notes.append("MACD positivo")
    elif (macd_hist.iloc[-1] < 0) and (macd_line.iloc[-1] < macd_sig.iloc[-1]): s_sell += 2; notes.append("MACD negativo")
    if patt['engolfo_bull'].iloc[-1] or patt['pinbar_bull'].iloc[-1] or patt['martelo'].iloc[-1]: s_buy += 1; notes.append("Padrão alta")
    if patt['engolfo_bear'].iloc[-1] or patt['pinbar_bear'].iloc[-1] or patt['estrela_cadente'].iloc[-1]: s_sell += 1; notes.append("Padrão baixa")
    if close.iloc[-1] <= bb_l.iloc[-1]: s_buy += 1; notes.append("Toque BB baixa")
    if close.iloc[-1] >= bb_h.iloc[-1]: s_sell += 1; notes.append("Toque BB alta")

    score_raw = max(s_buy, s_sell) / 8.0 * 100.0
    direcao = "compra" if s_buy >= s_sell else "venda"
    return { "score": round(score_raw,1), "direcao": direcao, "explicacao": notes }
