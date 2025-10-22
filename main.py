# ======================================================
# 🚀 IMPERADORVIP - IA Multi-Corretoras (Dados Reais + Telegram)
# Fonte de preços: TwelveData | Envio auto: ≥ 90% de confiança
# ======================================================

from fastapi import FastAPI, HTTPException, Request, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional, Any
import os
import requests
import pandas as pd
import numpy as np
import math
from datetime import datetime, timezone

# -----------------------------
# Configurações e Variáveis
# -----------------------------

APP_NAME = os.getenv("APP_NAME", "ImperadorVIP")
PORT = int(os.getenv("PORT", "8080"))
API_KEY = os.getenv("API_KEY", "imperadorvip-secure-key-2025")

# TwelveData
TWELVEDATA_KEY = os.getenv("TWELVEDATA_KEY", "")
TWELVEDATA_BASE = "https://api.twelvedata.com/time_series"

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Modo automático (env ou default off)
AUTO_MODE = os.getenv("AUTO_MODE", "false").lower() == "true"

# Timeout HTTP
HTTP_TIMEOUT = 12

# -----------------------------
# App + CORS
# -----------------------------

app = FastAPI(title=f"{APP_NAME} IA", version="4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # Base44, seu domínio custom e testes
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Corretores suportados e ativos
# (listas pragmáticas e realistas para validação/UX)
# -----------------------------

# Conjunto base de pares FX (TwelveData suporta os principais)
FX_BASE = [
    "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD", "NZD/USD",
    "USD/CAD", "EUR/GBP", "EUR/JPY", "GBP/JPY", "EUR/CHF",
    "USD/BRL", "USD/MXN", "EUR/BRL"  # pares latam
]

CRYPTO_BASE = [
    "BTC/USD", "ETH/USD", "SOL/USD", "BNB/USD", "XRP/USD", "DOGE/USD"
]

INDICES_BASE = [
    "US500", "NAS100", "US30", "DE40", "UK100", "JP225"
]

# Mapeamento simplificado por corretora
BROKER_UNIVERSE: Dict[str, Dict[str, List[str]]] = {
    "Quotex": {
        "forex": FX_BASE,
        "crypto": CRYPTO_BASE,
        "indices": INDICES_BASE,
        "binary_types": ["OTC", "Aberto"],  # rótulos de UI
    },
    "IQ Option": {
        "forex": FX_BASE,
        "crypto": CRYPTO_BASE,
        "indices": INDICES_BASE,
        "binary_types": ["Digital", "Binárias"],
    },
    "Deriv": {
        "forex": FX_BASE,
        "crypto": CRYPTO_BASE,
        "indices": INDICES_BASE,
        "binary_types": ["Volatility", "Synthetic"],
    },
    "Olymp Trade": {
        "forex": FX_BASE,
        "crypto": CRYPTO_BASE[:4],
        "indices": INDICES_BASE[:4],
        "binary_types": ["Tempo Fixo"],
    },
    "Binomo": {
        "forex": FX_BASE,
        "crypto": CRYPTO_BASE[:4],
        "indices": INDICES_BASE[:4],
        "binary_types": ["Tempo Fixo"],
    },
    "Avalon": {
        "forex": FX_BASE[:10],
        "crypto": CRYPTO_BASE[:4],
        "indices": INDICES_BASE[:3],
        "binary_types": ["OTC", "Aberto"],
    },
    "BulleX": {
        "forex": FX_BASE[:10],
        "crypto": CRYPTO_BASE[:4],
        "indices": INDICES_BASE[:3],
        "binary_types": ["OTC", "Aberto"],
    },
    "Casa Trader": {
        "forex": FX_BASE[:10],
        "crypto": CRYPTO_BASE[:4],
        "indices": INDICES_BASE[:3],
        "binary_types": ["OTC", "Aberto"],
    },
    "NexBroker": {
        "forex": FX_BASE[:10],
        "crypto": CRYPTO_BASE[:4],
        "indices": INDICES_BASE[:3],
        "binary_types": ["OTC", "Aberto"],
    },
    "Polaryum": {   # conforme você pediu a grafia
        "forex": FX_BASE,
        "crypto": CRYPTO_BASE,
        "indices": INDICES_BASE,
        "binary_types": ["OTC", "Aberto"],
    },
    "Broker10": {
        "forex": FX_BASE[:10],
        "crypto": CRYPTO_BASE[:3],
        "indices": INDICES_BASE[:3],
        "binary_types": ["OTC", "Aberto"],
    },
}

BROKERS_SUPPORTED = list(BROKER_UNIVERSE.keys())

# -----------------------------
# Helpers: intervals & símbolos
# -----------------------------

INTERVAL_MAP = {
    "M1": "1min", "1m": "1min", "1min": "1min",
    "M5": "5min", "5m": "5min",
    "M15": "15min", "15m": "15min",
    "M30": "30min", "30m": "30min",
    "H1": "1h", "1h": "1h",
}

def to_td_symbol(symbol: str) -> List[str]:
    """
    Normaliza o símbolo para a TwelveData.
    Tenta variações: "EUR/USD" -> ["EUR/USD", "EURUSD"]
    Índices como "US500" mantêm-se.
    Cripto idem.
    """
    s = symbol.strip().upper().replace(" ", "")
    candidates = [s]
    if "/" in s:
        candidates.append(s.replace("/", ""))
    return candidates

def http_get_json(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.get(url, params=params, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    return r.json()

def fetch_twelvedata(symbol: str, interval: str, outputsize: int = 150) -> pd.DataFrame:
    """
    Busca candles na TwelveData tentando variações do símbolo.
    Retorna DataFrame com colunas: open, high, low, close
    """
    if not TWELVEDATA_KEY:
        raise HTTPException(status_code=400, detail="TWELVEDATA_KEY não configurada.")
    td_interval = INTERVAL_MAP.get(interval, "1min")
    errors: List[str] = []

    for candidate in to_td_symbol(symbol):
        try:
            data = http_get_json(TWELVEDATA_BASE, {
                "symbol": candidate,
                "interval": td_interval,
                "apikey": TWELVEDATA_KEY,
                "outputsize": str(outputsize),
                "order": "desc",
            })
            if "values" in data:
                df = pd.DataFrame(data["values"])
                df = df.rename(columns=str.lower)
                # garantir tipos
                for col in ["open", "high", "low", "close"]:
                    df[col] = df[col].astype(float)
                # ordenar por tempo (asc)
                df = df.iloc[::-1].reset_index(drop=True)
                return df
            else:
                errors.append(f"{candidate}: resposta sem 'values' ({data.get('message') or data})")
        except Exception as ex:
            errors.append(f"{candidate}: {ex}")

    raise HTTPException(
        status_code=400,
        detail=f"TwelveData sem dados para {symbol} ({interval}). Tentativas: {errors}"
    )

# -----------------------------
# Indicadores e Padrões de Vela
# -----------------------------

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona RSI, EMAs, MACD, Bollinger e Stoch."""
    close = df["close"]
    high = df["high"]
    low = df["low"]

    # RSI
    rsi_period = 14
    delta = close.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.ewm(com=rsi_period-1, adjust=False).mean()
    ma_down = down.ewm(com=rsi_period-1, adjust=False).mean()
    rs = ma_up / (ma_down + 1e-9)
    df["rsi"] = 100 - (100 / (1 + rs))

    # EMA 9/21
    df["ema_fast"] = close.ewm(span=9, adjust=False).mean()
    df["ema_slow"] = close.ewm(span=21, adjust=False).mean()

    # MACD clássico 12/26/9
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal = macd_line.ewm(span=9, adjust=False).mean()
    df["macd"] = macd_line
    df["macd_signal"] = signal
    df["macd_hist"] = macd_line - signal

    # Bollinger (20, 2)
    ma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    df["bb_mid"] = ma20
    df["bb_up"] = ma20 + 2 * std20
    df["bb_low"] = ma20 - 2 * std20
    # largura
    df["bb_width"] = (df["bb_up"] - df["bb_low"]) / (df["bb_mid"] + 1e-9)

    # Stochastic %K (14), %D (3)
    low14 = low.rolling(14).min()
    high14 = high.rolling(14).max()
    df["stoch_k"] = (close - low14) / (high14 - low14 + 1e-9) * 100
    df["stoch_d"] = df["stoch_k"].rolling(3).mean()

    return df

def candle_patterns(df: pd.DataFrame) -> Dict[str, bool]:
    """Detecta alguns padrões fortes de reversão/continuação."""
    if len(df) < 3:
        return {"engulfing_bull": False, "engulfing_bear": False,
                "hammer": False, "shooting_star": False}

    c1 = df.iloc[-1]
    c0 = df.iloc[-2]

    # Corpo e sombras
    def candle_body(c): return abs(c["close"] - c["open"])
    def upper_shadow(c): return c["high"] - max(c["close"], c["open"])
    def lower_shadow(c): return min(c["close"], c["open"]) - c["low"]

    # Engolfo altista (corpo cobre o anterior e fecha acima)
    engulf_bull = ( (c1["close"] > c1["open"]) and
                    (c0["close"] < c0["open"]) and
                    (min(c1["open"], c1["close"]) <= min(c0["open"], c0["close"])) and
                    (max(c1["open"], c1["close"]) >= max(c0["open"], c0["close"])) )

    # Engolfo baixista
    engulf_bear = ( (c1["close"] < c1["open"]) and
                    (c0["close"] > c0["open"]) and
                    (min(c1["open"], c1["close"]) <= min(c0["open"], c0["close"])) and
                    (max(c1["open"], c1["close"]) >= max(c0["open"], c0["close"])) )

    # Martelo (pin bar inferior)
    body = candle_body(c1)
    ls = lower_shadow(c1)
    us = upper_shadow(c1)
    hammer = (ls > body * 2.5) and (us < body) and (c1["close"] > c1["open"])

    # Shooting Star (pin bar superior)
    shooting = (us > body * 2.5) and (ls < body) and (c1["close"] < c1["open"])

    return {
        "engulfing_bull": bool(engulf_bull),
        "engulfing_bear": bool(engulf_bear),
        "hammer": bool(hammer),
        "shooting_star": bool(shooting),
    }

# -----------------------------
# Estratégia & Confluências
# -----------------------------

def build_confluences(df: pd.DataFrame) -> Dict[str, Any]:
    """Gera confluências e um sinal provável."""
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else last

    confluences: List[str] = []
    score = 0

    # Tendência por EMAs
    if last["ema_fast"] > last["ema_slow"]:
        confluences.append("Tendência de alta (EMA 9>21)")
        score += 2
    elif last["ema_fast"] < last["ema_slow"]:
        confluences.append("Tendência de baixa (EMA 9<21)")
        score += 2

    # RSI
    if last["rsi"] < 30:
        confluences.append(f"RSI {last['rsi']:.1f} (sobrevendido)")
        score += 2
    elif last["rsi"] > 70:
        confluences.append(f"RSI {last['rsi']:.1f} (sobrecomprado)")
        score += 2

    # MACD histograma
    if last["macd_hist"] > 0 and prev["macd_hist"] <= 0:
        confluences.append("Cruzamento MACD para alta")
        score += 2
    elif last["macd_hist"] < 0 and prev["macd_hist"] >= 0:
        confluences.append("Cruzamento MACD para baixa")
        score += 2

    # Bollinger - contração / expansão
    if pd.notna(last["bb_width"]):
        if last["bb_width"] < df["bb_width"].rolling(20).mean().iloc[-1] * 0.8:
            confluences.append("Bollinger: contração (breakout possível)")
            score += 1

    # Estocástico
    if (last["stoch_k"] < 20) and (last["stoch_d"] < 20):
        confluences.append("Stoch em zona de compra (reversão provável)")
        score += 1
    elif (last["stoch_k"] > 80) and (last["stoch_d"] > 80):
        confluences.append("Stoch em zona de venda (reversão provável)")
        score += 1

    # Padrões de vela
    pats = candle_patterns(df)
    if pats["engulfing_bull"]:
        confluences.append("Padrão: Engolfo de Alta")
        score += 2
    if pats["engulfing_bear"]:
        confluences.append("Padrão: Engolfo de Baixa")
        score += 2
    if pats["hammer"]:
        confluences.append("Padrão: Martelo (Pin Bar)")
        score += 1
    if pats["shooting_star"]:
        confluences.append("Padrão: Shooting Star (Pin Bar)")
        score += 1

    # Derivação do sinal
    # Base: EMAs + RSI priorizam direção
    signal = "WAIT"
    if last["ema_fast"] > last["ema_slow"] and last["rsi"] < 70:
        signal = "CALL"
    if last["ema_fast"] < last["ema_slow"] and last["rsi"] > 30:
        signal = "PUT"

    # Ajustes por padrões fortes
    if pats["engulfing_bull"]:
        signal = "CALL"
    if pats["engulfing_bear"]:
        signal = "PUT"

    # Confiança: mapeia score (0..~12) para % 80..99
    # e penaliza se MACD e EMAs divergem
    base_conf = min(99.0, 80.0 + score * 1.8)
    if ( (last["ema_fast"] > last["ema_slow"] and last["macd_hist"] < 0) or
         (last["ema_fast"] < last["ema_slow"] and last["macd_hist"] > 0) ):
        base_conf -= 3.5

    confidence = max(50.0, min(99.0, base_conf))

    return {
        "signal": signal,
        "confidence": round(confidence, 2),
        "confluences": confluences,
        "patterns": pats
    }

# -----------------------------
# Telegram
# -----------------------------

def send_telegram(text: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        requests.post(url, json=payload, timeout=HTTP_TIMEOUT)
    except Exception:
        # não falha o fluxo por erro no telegram
        pass

# -----------------------------
# Middlewares simples
# -----------------------------

def require_api_key(x_api_key: Optional[str]):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="API key inválida.")

def validate_broker_symbol(broker: str, symbol: str) -> None:
    if broker not in BROKER_UNIVERSE:
        raise HTTPException(status_code=400, detail=f"Corretora não suportada: {broker}")

    universe = BROKER_UNIVERSE[broker]
    all_symbols = set(universe["forex"]) | set(universe["crypto"]) | set(universe["indices"])
    if symbol.upper() not in {s.upper() for s in all_symbols}:
        raise HTTPException(
            status_code=400,
            detail=f"Ativo '{symbol}' não disponível em {broker}. Consulte /assets?broker={broker}."
        )

# -----------------------------
# Endpoints
# -----------------------------

@app.get("/")
def root():
    return {
        "status": "online",
        "app": APP_NAME,
        "brokers_supported": BROKERS_SUPPORTED,
        "auto_mode": AUTO_MODE,
        "message": f"IA {APP_NAME} com dados reais (TwelveData) pronta."
    }

@app.get("/health")
@app.get("/_health")
def health():
    return {"status": "healthy", "brokers_count": len(BROKERS_SUPPORTED)}

@app.get("/config")
def config():
    return {
        "td_configured": bool(TWELVEDATA_KEY),
        "tg_configured": bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID),
        "auto_mode": AUTO_MODE,
        "http_timeout": HTTP_TIMEOUT
    }

@app.get("/assets")
def list_assets(broker: str = Query(..., description="Nome da corretora")):
    if broker not in BROKER_UNIVERSE:
        raise HTTPException(status_code=400, detail="Corretora não suportada.")
    u = BROKER_UNIVERSE[broker]
    return {
        "broker": broker,
        "types": u["binary_types"],
        "forex": u["forex"],
        "crypto": u["crypto"],
        "indices": u["indices"]
    }

@app.post("/bot/enable")
def bot_enable(x_api_key: Optional[str] = Header(None)):
    global AUTO_MODE
    require_api_key(x_api_key)
    AUTO_MODE = True
    return {"auto_mode": AUTO_MODE}

@app.post("/bot/disable")
def bot_disable(x_api_key: Optional[str] = Header(None)):
    global AUTO_MODE
    require_api_key(x_api_key)
    AUTO_MODE = False
    return {"auto_mode": AUTO_MODE}

@app.post("/analyze")
async def analyze(request: Request, x_api_key: Optional[str] = Header(None)):
    """
    Corpo esperado (JSON):
    {
      "broker": "Quotex",
      "symbol": "USD/BRL",
      "interval": "M1",          # M1, M5, M15, H1...
      "market": "OTC",           # rótulo informativo
      "expiry_minutes": 1        # opcional (1, 3, 5)
    }
    """
    require_api_key(x_api_key)

    body = await request.json()
    broker = (body.get("broker") or "").strip()
    symbol = (body.get("symbol") or "").strip().upper()
    interval = (body.get("interval") or "M1").strip()
    expiry_minutes = int(body.get("expiry_minutes", 1))
    market = (body.get("market") or "OTC").strip()

    if not broker or not symbol:
        raise HTTPException(status_code=400, detail="Parâmetros obrigatórios: broker e symbol.")

    # valida corretora/ativo
    validate_broker_symbol(broker, symbol)

    # busca candles
    df = fetch_twelvedata(symbol, interval, outputsize=180)
    if len(df) < 30:
        raise HTTPException(status_code=400, detail="Série curta demais para análise.")

    # indicadores e confluências
    df = compute_indicators(df)
    evald = build_confluences(df)
    signal = evald["signal"]
    confidence = evald["confidence"]
    confluences = evald["confluences"]
    patterns = evald["patterns"]
    last = df.iloc[-1]

    # Alvos (TP/SL) baseados na volatilidade recente (ATR simplificado)
    atr_like = (df["high"] - df["low"]).rolling(14).mean().iloc[-1]
    entry = float(last["close"])
    take_profit = entry + (atr_like * 0.8 if signal == "CALL" else -atr_like * 0.8)
    stop_loss   = entry - (atr_like * 0.8 if signal == "CALL" else -atr_like * 0.8)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "broker": broker,
        "symbol": symbol,
        "interval": interval,
        "market": market,
        "expiry_minutes": expiry_minutes,
        "last_price": round(entry, 6),
        "signal": signal,
        "confidence": confidence,
        "take_profit": round(take_profit, 6),
        "stop_loss": round(stop_loss, 6),
        "confluences": confluences,
        "patterns": patterns,
        "source": "TwelveData",
    }

    # Envio automático para Telegram somente se ≥ 90%
    if AUTO_MODE and confidence >= 90.0 and signal in ("CALL", "PUT"):
        msg = (
            f"📣 <b>{APP_NAME} • Sinal {signal}</b>\n"
            f"• Corretora: <b>{broker}</b>\n"
            f"• Ativo: <b>{symbol}</b>  • TF: <b>{interval}</b>  • Mercado: <b>{market}</b>\n"
            f"• Expiração: <b>{expiry_minutes}m</b>\n"
            f"• Preço: <code>{payload['last_price']}</code>\n"
            f"• Confiança: <b>{confidence:.2f}%</b>\n"
            f"• Confluências: {', '.join(confluences[:4])}...\n"
            f"• TP: <code>{payload['take_profit']}</code> • SL: <code>{payload['stop_loss']}</code>\n"
            f"⏱ {payload['timestamp']}"
        )
        send_telegram(msg)

    return payload

# -----------------------------
# Execução local
# -----------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
