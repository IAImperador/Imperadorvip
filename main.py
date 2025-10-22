# ======================================================
# 🚀 IMPERADORVIP - IA de Confluência Multi-Corretoras (Real-Time)
# Back-end para Base44 + Railway + Telegram
# Versão 4.5 — Indicadores + Padrões + Confluências Profissionais
# ======================================================

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Tuple

import os, requests
import pandas as pd
import numpy as np
import ta

# ------------------------------------------------------
# App + CORS
# ------------------------------------------------------
app = FastAPI(title="ImperadorVIP IA", version="4.5")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://imperadorvip.base44.app",
        "https://app.base44.io",
        "https://studio.base44.io",
        "https://base44.app",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------
# Env
# ------------------------------------------------------
APP_NAME        = os.getenv("APP_NAME", "ImperadorVIP")
PORT            = int(os.getenv("PORT", "8080"))
API_KEY         = os.getenv("API_KEY", "imperadorvip-secure-key-2025")

TWELVEDATA_KEY  = os.getenv("TWELVEDATA_KEY", "demo")  # coloque sua chave real
TD_BASE         = "https://api.twelvedata.com"
HTTP_TIMEOUT    = 12

TG_TOKEN        = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT         = os.getenv("TELEGRAM_CHAT_ID", "")
BOT_AUTO        = os.getenv("BOT_AUTO", "false").lower() == "true"

# ======================================================
# 📚 Catálogo de corretoras e ativos (ajustável)
# ======================================================
BROKERS: Dict[str, Dict[str, List[str]]] = {
    "Deriv": {
        "binaria": ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"],
        "indices": ["US500", "NAS100", "JPN225"],
        "cripto":  ["BTC/USD", "ETH/USD"],
    },
    "Quotex": {
        "binaria": ["EUR/USD", "GBP/USD", "USD/JPY", "EUR/JPY", "AUD/USD"],
        "cripto":  ["BTC/USD", "ETH/USD"],
        "commodities": ["XAU/USD", "XAG/USD"],
    },
    "IQ Option": {
        "digital": ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"],
        "binaria": ["EUR/JPY", "USD/CHF"],
        "cripto":  ["BTC/USD", "ETH/USD"],
        "indices": ["US500", "NAS100"],
    },
    "Binomo": {
        "binaria": ["EUR/USD", "USD/JPY", "GBP/USD", "EUR/JPY"],
        "cripto":  ["BTC/USD"],
    },
    "Pocket Option": {
        "binaria": ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"],
        "cripto":  ["BTC/USD", "ETH/USD"],
    },
    "Olymp Trade": {
        "binaria": ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "EUR/JPY"],
        "indices": ["US500"],
    },
    "Avalon": {
        "binaria": ["EUR/USD", "USD/JPY", "GBP/USD"],
    },
    "BulleX": {
        "binaria": ["EUR/USD", "GBP/USD", "USD/JPY"],
        "cripto":  ["BTC/USD"],
    },
    "Casa Trader": {
        "binaria": ["EUR/USD", "USD/JPY", "GBP/USD"],
    },
    "NexBroker": {
        "binaria": ["EUR/USD", "GBP/USD", "USD/JPY"],
        "indices": ["US500"],
    },
    # Escritas corrigidas conforme você pediu:
    "Polaryum": {
        "binaria": ["EUR/USD", "GBP/USD", "USD/JPY"],
    },
    "Broker10": {
        "binaria": ["EUR/USD", "USD/JPY", "GBP/USD"],
    },
}

SUPPORTED_INTERVALS = {
    "M1": "1min",
    "M5": "5min",
    "M15": "15min",
    "M30": "30min",
    "H1": "1h",
    "H4": "4h",
}

# ======================================================
# 🧩 Utilidades HTTP / Telegram
# ======================================================

def _normalize_symbol_for_td(symbol: str) -> str:
    return symbol.strip().upper()

def _fetch_series_from_twelvedata(symbol: str, td_interval: str, outputsize: int = 500) -> pd.DataFrame:
    url = f"{TD_BASE}/time_series"
    params = {
        "symbol": symbol,
        "interval": td_interval,
        "apikey": TWELVEDATA_KEY,
        "outputsize": outputsize,
        "order": "desc",
    }
    r = requests.get(url, params=params, timeout=HTTP_TIMEOUT)
    data = r.json()
    if "values" not in data:
        raise HTTPException(status_code=400, detail=f"Erro TwelveData: {data.get('message','dados ausentes')}")
    df = pd.DataFrame(data["values"])
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)
    if "volume" in df.columns:
        df["volume"] = df["volume"].astype(float)
    else:
        # Alguns símbolos/intervalos não trazem volume → assuma 0
        df["volume"] = 0.0
    # ordem cronológica crescente
    df = df.iloc[::-1].reset_index(drop=True)
    return df

def _tg_send(text: str) -> None:
    if not TG_TOKEN or not TG_CHAT:
        return
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {"chat_id": TG_CHAT, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
        requests.post(url, json=payload, timeout=HTTP_TIMEOUT)
    except Exception:
        pass

# ======================================================
# 🧠 Cálculo de Indicadores
# ======================================================

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    close = df["close"]
    high  = df["high"]
    low   = df["low"]
    vol   = df["volume"]

    # Tendência / Médias
    df["ema9"]   = ta.trend.EMAIndicator(close, window=9).ema_indicator()
    df["ema21"]  = ta.trend.EMAIndicator(close, window=21).ema_indicator()
    df["sma50"]  = close.rolling(50).mean()
    df["sma200"] = close.rolling(200).mean()

    # Momentum
    rsi = ta.momentum.RSIIndicator(close, window=14)
    df["rsi"]    = rsi.rsi()
    macd = ta.trend.MACD(close)
    df["macd"]   = macd.macd()
    df["macd_sig"]= macd.macd_signal()
    df["roc"]    = ta.momentum.ROCIndicator(close, window=12).roc()

    # Volatilidade
    bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
    df["bb_h"] = bb.bollinger_hband()
    df["bb_l"] = bb.bollinger_lband()
    df["atr"]  = ta.volatility.AverageTrueRange(high, low, close, window=14).average_true_range()

    # Osciladores adicionais
    df["stoch"] = ta.momentum.StochasticOscillator(high, low, close, window=14, smooth_window=3).stoch()
    df["cci"]   = ta.trend.CCIIndicator(high, low, close, window=20).cci()
    df["wr"]    = ta.momentum.WilliamsRIndicator(high, low, close, lbp=14).williams_r()
    df["adx"]   = ta.trend.ADXIndicator(high, low, close, window=14).adx()

    # Volume/Fluxo
    df["obv"]   = ta.volume.OnBalanceVolumeIndicator(close, vol).on_balance_volume()
    mfi = ta.volume.MFIIndicator(high, low, close, vol, window=14)
    df["mfi"]   = mfi.money_flow_index()

    return df

# ======================================================
# 🕯️ Padrões de Vela (detecção simples, eficiente)
# ======================================================

def _body(o, c): return abs(c - o)
def _upper_shadow(h, o, c): return h - max(o, c)
def _lower_shadow(l, o, c): return min(o, c) - l

def detect_candles(df: pd.DataFrame) -> Dict[str, bool]:
    """Detecta alguns padrões clássicos na última barra."""
    i = len(df) - 1
    if i < 3:
        return {}

    o = df["open"].iloc[i]; c = df["close"].iloc[i]
    h = df["high"].iloc[i]; l = df["low"].iloc[i]
    prev_o = df["open"].iloc[i-1]; prev_c = df["close"].iloc[i-1]

    rng = max(1e-9, h - l)
    body = _body(o, c)
    us   = _upper_shadow(h, o, c)
    ls   = _lower_shadow(l, o, c)

    small_body  = body <= 0.25 * rng
    long_body   = body >= 0.6  * rng
    long_upper  = us   >= 0.6  * rng
    long_lower  = ls   >= 0.6  * rng

    bull = c > o
    bear = c < o

    # Engolfo
    bull_engulf = bull and (o <= prev_c) and (c >= prev_o) and (prev_c < prev_o)
    bear_engulf = bear and (o >= prev_c) and (c <= prev_o) and (prev_c > prev_o)

    # Doji
    doji = small_body and us > 0.1*rng and ls > 0.1*rng

    # Martelo (hammer) e invertido
    hammer = long_lower and not long_upper and small_body and bull
    inv_hammer = long_upper and not long_lower and small_body and bull

    # Shooting Star / Estrela Cadente
    shooting = long_upper and small_body and bear

    # Harami (pequeno corpo dentro do corpo anterior)
    prev_body_high = max(prev_o, prev_c)
    prev_body_low  = min(prev_o, prev_c)
    harami_bull = bull and (max(o,c) < prev_body_high) and (min(o,c) > prev_body_low) and (prev_c < prev_o)
    harami_bear = bear and (max(o,c) < prev_body_high) and (min(o,c) > prev_body_low) and (prev_c > prev_o)

    # Três Soldados Brancos / Três Corvos Pretos (simples)
    last3 = df.iloc[i-2:i+1]
    tres_soldados = (last3["close"] > last3["open"]).all() and (last3["close"].diff() > 0).all()
    tres_corvos   = (last3["close"] < last3["open"]).all() and (last3["close"].diff() < 0).all()

    return {
        "bull_engulf": bool(bull_engulf),
        "bear_engulf": bool(bear_engulf),
        "doji": bool(doji),
        "hammer": bool(hammer),
        "inverted_hammer": bool(inv_hammer),
        "shooting_star": bool(shooting),
        "harami_bull": bool(harami_bull),
        "harami_bear": bool(harami_bear),
        "three_white_soldiers": bool(tres_soldados),
        "three_black_crows": bool(tres_corvos),
    }

# ======================================================
# 📈 S/R, LTA/LTB, Canal, Fibonacci, Regras auxiliares
# ======================================================

def rolling_pivots(df: pd.DataFrame, win: int = 20) -> Tuple[float, float]:
    """Suporte/Resistência por máximas/mínimas recentes."""
    recent = df.tail(win)
    return float(recent["low"].min()), float(recent["high"].max())

def trend_line(df: pd.DataFrame, win: int = 50) -> Tuple[float, float]:
    """
    Ajuste de regressão linear simples sobre 'close' para estimar LTA/LTB.
    Retorna (slope, last_fit_value).
    """
    if len(df) < win: win = len(df)
    y = df["close"].tail(win).values
    x = np.arange(len(y))
    # coeficientes da reta y = ax + b
    a, b = np.polyfit(x, y, 1)
    return float(a), float(a * (len(x)-1) + b)

def channel_bounds(df: pd.DataFrame, win: int = 50, dev: float = 1.5) -> Tuple[float, float]:
    """Canal por regressão + desvio padrão."""
    if len(df) < win: win = len(df)
    y = df["close"].tail(win).values
    x = np.arange(len(y))
    a, b = np.polyfit(x, y, 1)
    fit = a * x + b
    std = np.std(y - fit)
    return float(fit[-1] - dev*std), float(fit[-1] + dev*std)

def fibo_retracement(df: pd.DataFrame, win: int = 60) -> Dict[str, float]:
    """Níveis de Fibonacci do último swing."""
    if len(df) < win: win = len(df)
    seg = df.tail(win)
    high = float(seg["high"].max())
    low  = float(seg["low"].min())
    diff = high - low if high != low else 1e-9
    return {
        "0.0": high,
        "0.236": high - 0.236*diff,
        "0.382": high - 0.382*diff,
        "0.5": high - 0.5*diff,
        "0.618": high - 0.618*diff,
        "0.786": high - 0.786*diff,
        "1.0": low
    }

def daily_price_limits(df: pd.DataFrame) -> Tuple[float, float]:
    """Faixa diária simples (últimas 24 barras se M1)."""
    recent = df.tail(24) if len(df) >= 24 else df
    return float(recent["low"].min()), float(recent["high"].max())

def first_bar_of_session(df: pd.DataFrame) -> bool:
    """Proxy simples: primeira barra do último bloco de 60 (apenas para ponderar)."""
    return (len(df) % 60) == 1

# ======================================================
# 🧮 Motor de Confluência (pontuação -> sinal)
# ======================================================

def confluence_engine(df: pd.DataFrame) -> Dict:
    """
    Combina indicadores, padrões e estruturas em uma pontuação 0..100.
    Regras desenhadas para estabilidade (não quebrar se faltar dado).
    """
    i = len(df) - 1
    c = df["close"].iloc[i]
    o = df["open"].iloc[i]
    h = df["high"].iloc[i]
    l = df["low"].iloc[i]

    # --- Indicadores (com try para blindagem) ---
    score = 50  # base neutra
    reasons = []

    try:
        # Tendência
        if df["ema9"].iloc[i] > df["ema21"].iloc[i]: score += 4; reasons.append("EMA9>EMA21")
        if df["sma50"].iloc[i] > df["sma200"].iloc[i]: score += 3; reasons.append("SMA50>SMA200")
        if df["adx"].iloc[i] > 20:
            reasons.append("ADX>20")
            score += 2

        # Momentum / Osciladores
        if df["rsi"].iloc[i] < 30: score += 5; reasons.append("RSI<30")
        elif df["rsi"].iloc[i] > 70: score -= 5; reasons.append("RSI>70")

        if df["stoch"].iloc[i] < 20: score += 4; reasons.append("Stoch<20")
        elif df["stoch"].iloc[i] > 80: score -= 4; reasons.append("Stoch>80")

        if df["macd"].iloc[i] > df["macd_sig"].iloc[i]: score += 3; reasons.append("MACD>Signal")
        else: score -= 1

        if df["wr"].iloc[i] < -80: score += 2; reasons.append("W%R<-80")
        elif df["wr"].iloc[i] > -20: score -= 2; reasons.append("W%R>-20")

        if df["cci"].iloc[i] < -100: score += 2; reasons.append("CCI<-100")
        elif df["cci"].iloc[i] > 100: score -= 2; reasons.append("CCI>100")

        if df["mfi"].iloc[i] < 20: score += 2; reasons.append("MFI<20")
        elif df["mfi"].iloc[i] > 80: score -= 2; reasons.append("MFI>80")

        # Volatilidade / Bandas
        if c <= df["bb_l"].iloc[i]: score += 3; reasons.append("Preço na banda inferior")
        if c >= df["bb_h"].iloc[i]: score -= 3; reasons.append("Preço na banda superior")

        # Momentum adicional
        if df["roc"].iloc[i] > 0: score += 1
        else: score -= 1
    except Exception:
        pass

    # --- Padrões de vela ---
    try:
        patt = detect_candles(df)
        if patt.get("hammer"): score += 4; reasons.append("Hammer")
        if patt.get("inverted_hammer"): score += 2; reasons.append("Inverted Hammer")
        if patt.get("shooting_star"): score -= 4; reasons.append("Shooting Star")
        if patt.get("bull_engulf"): score += 5; reasons.append("Bull Engulf")
        if patt.get("bear_engulf"): score -= 5; reasons.append("Bear Engulf")
        if patt.get("harami_bull"): score += 2; reasons.append("Harami Bull")
        if patt.get("harami_bear"): score -= 2; reasons.append("Harami Bear")
        if patt.get("three_white_soldiers"): score += 6; reasons.append("3 White Soldiers")
        if patt.get("three_black_crows"): score -= 6; reasons.append("3 Black Crows")
        if patt.get("doji"): reasons.append("Doji (neutro)")
    except Exception:
        pass

    # --- Estruturas: S/R, LTA/LTB, Canal, Fibo ---
    try:
        sup, res = rolling_pivots(df, win=20)
        if c <= sup * 1.001: score += 3; reasons.append("Na região de Suporte")
        if c >= res * 0.999: score -= 3; reasons.append("Na região de Resistência")
    except Exception:
        pass

    try:
        slope, last_fit = trend_line(df, win=50)
        if slope > 0: score += 2; reasons.append("LTA")
        elif slope < 0: score -= 2; reasons.append("LTB")
    except Exception:
        pass

    try:
        ch_low, ch_high = channel_bounds(df, win=50, dev=1.6)
        if c <= ch_low: score += 2; reasons.append("Canal - base")
        if c >= ch_high: score -= 2; reasons.append("Canal - topo")
    except Exception:
        pass

    try:
        fib = fibo_retracement(df, win=60)
        # aproximações a 0.382/0.618 ajudam a reversão
        if abs(c - fib["0.618"]) <= (df["atr"].iloc[-1] * 0.2): score += 2; reasons.append("Fibo 61.8%")
        if abs(c - fib["0.382"]) <= (df["atr"].iloc[-1] * 0.2): score += 1; reasons.append("Fibo 38.2%")
    except Exception:
        pass

    # --- Regras auxiliares ---
    try:
        dmin, dmax = daily_price_limits(df)
        if c <= dmin * 1.001: score += 1; reasons.append("Limite diário inferior")
        if c >= dmax * 0.999: score -= 1; reasons.append("Limite diário superior")
    except Exception:
        pass

    try:
        if first_bar_of_session(df): reasons.append("Primeiro registro da sessão"); score = int(score * 0.9)
    except Exception:
        pass

    # Clamp e decisão
    score = int(max(0, min(100, score)))
    if score >= 62:
        signal = "CALL"
    elif score <= 38:
        signal = "PUT"
    else:
        signal = "WAIT"

    return {"signal": signal, "confidence": score, "reasons": reasons}

# ======================================================
# 🔌 Modelos
# ======================================================

class AnalyzePayload(BaseModel):
    broker: str
    symbol: str
    timeframe: str = "M1"            # M1/M5/M15/M30/H1/H4
    market: Optional[str] = "OTC"
    auto: Optional[bool] = False

# ======================================================
# 🌐 Endpoints
# ======================================================

@app.get("/")
def root():
    return {
        "status": "online",
        "app": APP_NAME,
        "message": f"IA {APP_NAME} ligada com sucesso.",
        "brokers_enabled": list(BROKERS.keys()),
        "bot_auto": BOT_AUTO,
    }

@app.get("/health")
def health():
    return {"status": "healthy", "brokers_count": len(BROKERS), "bot_auto": BOT_AUTO}

@app.get("/brokers")
def list_brokers():
    return {"brokers": list(BROKERS.keys())}

@app.get("/catalog")
def catalog():
    return {"catalog": BROKERS}

@app.get("/assets")
def assets(broker: str = Query(..., description="Nome exato da corretora")):
    broker = broker.strip()
    if broker not in BROKERS:
        raise HTTPException(status_code=404, detail=f"Broker '{broker}' não suportado.")
    return {"broker": broker, "assets": BROKERS[broker]}

@app.post("/analyze")
def analyze(payload: AnalyzePayload):
    broker = payload.broker.strip()
    if broker not in BROKERS:
        raise HTTPException(status_code=404, detail=f"Broker '{broker}' não suportado.")

    tf = payload.timeframe.upper().strip()
    if tf not in SUPPORTED_INTERVALS:
        raise HTTPException(status_code=400, detail=f"Timeframe inválido. Use {list(SUPPORTED_INTERVALS.keys())}.")

    symbol = payload.symbol.strip().upper()
    broker_assets_flat = {a for lst in BROKERS[broker].values() for a in lst}
    if symbol not in broker_assets_flat:
        raise HTTPException(status_code=400, detail=f"O ativo '{symbol}' não existe/está habilitado na corretora '{broker}'.")

    td_symbol  = _normalize_symbol_for_td(symbol)
    td_interval= SUPPORTED_INTERVALS[tf]

    try:
        df = _fetch_series_from_twelvedata(td_symbol, td_interval, outputsize=500)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Falha ao buscar dados: {str(e)}")

    try:
        df = compute_indicators(df)
        decision = confluence_engine(df)
        last = len(df) - 1
        last_price = float(df["close"].iloc[last])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na análise: {str(e)}")

    result = {
        "broker": broker,
        "symbol": symbol,
        "timeframe": tf,
        "market": payload.market,
        "last_price": last_price,
        "signal": decision["signal"],
        "confidence": decision["confidence"],
        "reasons": decision["reasons"],
        "indicators": {
            "rsi": round(float(df["rsi"].iloc[-1]), 2),
            "ema9": round(float(df["ema9"].iloc[-1]), 5),
            "ema21": round(float(df["ema21"].iloc[-1]), 5),
            "sma50": round(float(df["sma50"].iloc[-1]) if not np.isnan(df["sma50"].iloc[-1]) else float("nan"), 5),
            "sma200": round(float(df["sma200"].iloc[-1]) if not np.isnan(df["sma200"].iloc[-1]) else float("nan"), 5),
            "macd": round(float(df["macd"].iloc[-1]), 5),
            "stoch": round(float(df["stoch"].iloc[-1]), 2),
            "adx": round(float(df["adx"].iloc[-1]), 2),
            "atr": round(float(df["atr"].iloc[-1]), 5),
            "bb_h": round(float(df["bb_h"].iloc[-1]), 5),
            "bb_l": round(float(df["bb_l"].iloc[-1]), 5),
            "cci": round(float(df["cci"].iloc[-1]), 2),
            "wr": round(float(df["wr"].iloc[-1]), 2),
            "mfi": round(float(df["mfi"].iloc[-1]), 2),
            "roc": round(float(df["roc"].iloc[-1]), 2),
        }
    }

    # envio opcional ao Telegram
    if payload.auto and BOT_AUTO and decision["signal"] in ("CALL", "PUT"):
        msg = (
            f"⚡ <b>ImperadorVIP - Sinal</b>\n"
            f"Corretora: <b>{broker}</b>\n"
            f"Ativo: <b>{symbol}</b>\n"
            f"Timeframe: <b>{tf}</b>\n"
            f"Sinal: <b>{decision['signal']}</b>\n"
            f"Confiança: <b>{decision['confidence']}%</b>\n"
            f"Preço: <b>{last_price}</b>"
        )
        _tg_send(msg)

    return result

# -----------------------------
# Bot Telegram - controle
# -----------------------------
@app.get("/bot/status")
def bot_status():
    return {"enabled": BOT_AUTO, "has_token": bool(TG_TOKEN), "chat": TG_CHAT or "(não configurado)"}

@app.post("/bot/enable")
def bot_enable():
    global BOT_AUTO
    if not TG_TOKEN or not TG_CHAT:
        raise HTTPException(status_code=400, detail="Configure TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID.")
    BOT_AUTO = True
    return {"enabled": BOT_AUTO}

@app.post("/bot/disable")
def bot_disable():
    global BOT_AUTO
    BOT_AUTO = False
    return {"enabled": BOT_AUTO}

# ======================================================
# 🧩 Execução local
# ======================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
