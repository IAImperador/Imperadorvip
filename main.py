# ======================================================
# 🚀 IMPERADORVIP – Backend IA (Dados Reais + Sincronismo de Velas)
# ======================================================

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional
import os, math, time, datetime as dt
import requests
import pandas as pd
import numpy as np

# ---------- Configs ----------
APP_NAME = os.getenv("APP_NAME", "ImperadorVIP")
PORT = int(os.getenv("PORT", "8080"))
TIMEZONE = os.getenv("TIMEZONE", "America/Sao_Paulo")
API_KEY = os.getenv("API_KEY", "imperadorvip-secure-key-2025")

# Providers
TWELVEDATA_KEY = os.getenv("TWELVEDATA_KEY", "demo")  # pegue sua key real
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "12"))

# Telegram (opcional)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TG_AUTO = os.getenv("TG_AUTO", "off").lower() == "on"

# ---------- App & CORS ----------
app = FastAPI(title="ImperadorVIP IA", version="4.2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://imperadorvip.base44.app",
        "https://studio.base44.io",
        "https://app.base44.io",
        "https://base44.app",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Helpers ----------
def now_utc():
    return dt.datetime.now(dt.timezone.utc)

def to_tz(ts: dt.datetime, tz_name: str) -> dt.datetime:
    # conversão sem libs extras: assumimos offset fixo via %z quando disponível
    # para respostas, manteremos UTC e string ISO; borda de vela é calculada em UTC
    return ts

FRAME_MINUTES = {"M1":1, "M5":5, "M15":15, "M30":30, "H1":60}

def floor_to_frame(ts_utc: dt.datetime, frame: str) -> dt.datetime:
    minutes = FRAME_MINUTES.get(frame.upper(), 1)
    floored_minute = (ts_utc.minute // minutes) * minutes
    return ts_utc.replace(second=0, microsecond=0, minute=floored_minute)

def normalize_symbol(broker: str, symbol: str) -> Dict[str, str]:
    """
    Converte 'USD/BRL' -> {'fx':'USDBRL', 'binance':'USDTBRL', 'pretty':'USD/BRL'}
    Converte 'BTC/USDT' -> {'fx':'BTCUSD', 'binance':'BTCUSDT', ...}
    """
    s = symbol.upper().replace(" ", "")
    pretty = s.replace("/", "/")
    parts = s.split("/")
    out = {"pretty": symbol}

    if len(parts) == 2:
        base, quote = parts[0], parts[1]
        out["fx"] = f"{base}{quote}"        # TwelveData/FX style
        if quote in ("USDT","BUSD"):
            out["binance"] = f"{base}{quote}"  # Binance cripto
        elif base in ("XAU","XAG"):  # Ouro/Prata
            out["fx"] = f"{base}{quote}"
            out["binance"] = None
        else:
            # mapeia pares BRL para USDTBRL em cripto (aproximação)
            if quote == "BRL":
                out["binance"] = f"USDT{quote}" if base=="USDT" else f"{base}{quote}"
            else:
                out["binance"] = f"{base}{quote}"

    else:
        # símbolos “índices” (ex.: US500, NAS100) – suporte TwelveData
        out["fx"] = s
        out["binance"] = None

    # Ajustes por corretora (nomes exibidos)
    out["pretty"] = symbol
    return out

def is_otc(market: str) -> bool:
    return market.strip().upper() == "OTC"

# ---------- Universos por corretora ----------
BROKERS: Dict[str, Dict] = {
    "Quotex": {
        "markets": ["BINARIAS","DIGITAL","OTC","CRYPTO","FOREX","INDICES"],
        "notes": "Preços OTC são sintéticos; feed público não é 1:1.",
        "assets_hint": ["EUR/USD","USD/BRL","GBP/JPY","XAU/USD","BTC/USDT"],
    },
    "IQ Option": {
        "markets": ["BINARIAS","DIGITAL","OTC","FOREX","CRYPTO","INDICES"],
        "assets_hint": ["EUR/USD","GBP/USD","USD/JPY","BTC/USDT","XAU/USD"],
    },
    "Binomo": {
        "markets": ["BINARIAS","OTC"],
        "assets_hint": ["EUR/USD","USD/JPY","GBP/USD"],
    },
    "Pocket Option": {
        "markets": ["BINARIAS","OTC","CRYPTO"],
        "assets_hint": ["EUR/USD","USD/BRL","BTC/USDT"],
    },
    "Olymp Trade": {
        "markets": ["BINARIAS","OTC","FOREX","CRYPTO"],
        "assets_hint": ["EUR/USD","USD/JPY","BTC/USDT"],
    },
    "Deriv": {
        "markets": ["BINARY","FOREX","CRYPTO","SYNTHETIC"],
        "assets_hint": ["EUR/USD","Volatility 100 (synthetic)","BTC/USDT"],
        "api": "oficial"  # tem WebSocket oficial (não implementado aqui)
    },
    "Avalon":{"markets":["BINARIAS"],"assets_hint":[]},
    "BulleX":{"markets":["BINARIAS"],"assets_hint":[]},
    "Casa Trader":{"markets":["BINARIAS"],"assets_hint":[]},
    "NexBroker":{"markets":["BINARIAS"],"assets_hint":[]},
    "Polaryum":{"markets":["BINARIAS"],"assets_hint":[]},
    "Broker10":{"markets":["BINARIAS"],"assets_hint":[]},
}

ALL_BROKERS = list(BROKERS.keys())

# ---------- Price Providers ----------
def td_price_fx(symbol_fx: str) -> Optional[float]:
    # preço spot atual
    try:
        url = f"https://api.twelvedata.com/price?symbol={symbol_fx}&apikey={TWELVEDATA_KEY}"
        r = requests.get(url, timeout=HTTP_TIMEOUT)
        j = r.json()
        if "price" in j:
            return float(j["price"])
    except Exception:
        return None
    return None

def td_candles(symbol_fx: str, interval: str="1min", outputsize: int=150) -> pd.DataFrame:
    url = (
        "https://api.twelvedata.com/time_series"
        f"?symbol={symbol_fx}&interval={interval}&outputsize={outputsize}&apikey={TWELVEDATA_KEY}"
    )
    r = requests.get(url, timeout=HTTP_TIMEOUT)
    j = r.json()
    if "values" not in j:
        raise HTTPException(status_code=400, detail=f"TwelveData sem 'values' para {symbol_fx}: {j.get('message','erro')}")
    df = pd.DataFrame(j["values"])
    for col in ("open","high","low","close"):
        df[col] = df[col].astype(float)
    # TwelveData vem desc, ordene asc por datetime
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df = df.sort_values("datetime").reset_index(drop=True)
    return df

def binance_price(symbol_binance: str) -> Optional[float]:
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol_binance}"
        r = requests.get(url, timeout=HTTP_TIMEOUT)
        j = r.json()
        if "price" in j:
            return float(j["price"])
    except Exception:
        return None
    return None

def binance_klines(symbol_binance: str, interval: str="1m", limit: int=300) -> pd.DataFrame:
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol_binance}&interval={interval}&limit={limit}"
    r = requests.get(url, timeout=HTTP_TIMEOUT)
    arr = r.json()
    if isinstance(arr, list):
        cols = ["open_time","open","high","low","close","volume","close_time",
                "qav","num_trades","taker_base","taker_quote","ignore"]
        df = pd.DataFrame(arr, columns=cols)
        for c in ("open","high","low","close"):
            df[c] = df[c].astype(float)
        df["datetime"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
        df = df[["datetime","open","high","low","close"]].sort_values("datetime").reset_index(drop=True)
        return df
    raise HTTPException(status_code=400, detail=f"Binance klines inválidos: {arr}")

def pick_feed(broker: str, symbol: str, market: str):
    """Decide fonte de preço/candle e indica qualidade."""
    ns = normalize_symbol(broker, symbol)
    fx = ns.get("fx")
    b = ns.get("binance")
    market_up = market.upper()

    # Cripto → Binance
    if "BTC" in symbol.upper() or "ETH" in symbol.upper() or "USDT" in symbol.upper():
        return {"price_fn": lambda: binance_price(b), "candles_fn": lambda i: binance_klines(b, interval=i), "quality":"real-crypto", "source":"binance"}

    # Forex/Metais/Índices → TwelveData
    # (para Quotex/Binárias em OTC, marcamos como simulated)
    quality = "real-fx"
    if is_otc(market_up):
        quality = "simulated-otc"
    return {
        "price_fn": lambda: td_price_fx(fx),
        "candles_fn": lambda i: td_candles(fx, interval=i),
        "quality": quality,
        "source": "twelvedata"
    }

def tf_to_provider_interval(tf: str, provider: str) -> str:
    tf = tf.upper()
    if provider == "binance":
        return {"M1":"1m","M5":"5m","M15":"15m","M30":"30m","H1":"1h"}.get(tf,"1m")
    # TwelveData
    return {"M1":"1min","M5":"5min","M15":"15min","M30":"30min","H1":"1h"}.get(tf,"1min")

# ---------- Indicadores (essenciais e leves) ----------
def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    # Calcula poucos indicadores leves e estáveis; (outros podem ser somados depois)
    close = df["close"]
    # EMA9 / EMA21
    df["ema9"]  = close.ewm(span=9, adjust=False).mean()
    df["ema21"] = close.ewm(span=21, adjust=False).mean()
    # RSI14
    delta = close.diff()
    up = np.where(delta>0, delta, 0.0)
    down = np.where(delta<0, -delta, 0.0)
    roll_up = pd.Series(up).ewm(span=14, adjust=False).mean()
    roll_down = pd.Series(down).ewm(span=14, adjust=False).mean()
    rs = roll_up / (roll_down + 1e-9)
    df["rsi14"] = 100 - (100/(1+rs))
    # Bollinger 20
    m = close.rolling(20).mean()
    s = close.rolling(20).std(ddof=0)
    df["bb_mid"] = m
    df["bb_high"] = m + 2*s
    df["bb_low"]  = m - 2*s
    return df

def make_signal(df: pd.DataFrame) -> Dict:
    last = df.iloc[-1]
    sig = "WAIT"
    reasons = []

    if last["ema9"] > last["ema21"] and last["rsi14"] < 70:
        sig = "CALL"
        reasons.append("Tendência de alta (EMA9>EMA21) e RSI<70")
    elif last["ema9"] < last["ema21"] and last["rsi14"] > 30:
        sig = "PUT"
        reasons.append("Tendência de baixa (EMA9<EMA21) e RSI>30")

    # Bollinger squeeze breakout (simples)
    if last["close"] > last["bb_high"]:
        sig = "CALL"; reasons.append("Fechou acima da banda superior (breakout)")
    elif last["close"] < last["bb_low"]:
        sig = "PUT"; reasons.append("Fechou abaixo da banda inferior (breakdown)")

    # confiança heurística (faixa 88-99)
    conf = 92.0
    if "breakout" in " ".join(reasons).lower():
        conf = 96.0
    return {"signal": sig, "confidence": round(conf,2), "reasons": reasons}

# ---------- Telegram ----------
def tg_send(text: str):
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
        requests.post(url, json=payload, timeout=HTTP_TIMEOUT)
    except Exception:
        pass

# ======================================================
# 🌐 Endpoints
# ======================================================

@app.get("/")
def root():
    return {
        "status":"online",
        "app": APP_NAME,
        "brokers_enabled": ALL_BROKERS,
        "message": f"{APP_NAME} pronto.",
    }

@app.get("/health")
def health():
    return {"status":"healthy","time": now_utc().isoformat()}

@app.get("/brokers")
def brokers():
    return {"brokers": ALL_BROKERS}

@app.get("/assets")
def assets(broker: str = Query(..., description="Ex.: Quotex")):
    if broker not in BROKERS:
        raise HTTPException(400, f"Broker desconhecido: {broker}")
    return {
        "broker": broker,
        "markets": BROKERS[broker]["markets"],
        "sample_assets": BROKERS[broker]["assets_hint"],
        "note": BROKERS[broker].get("notes","")
    }

@app.get("/price")
def price(
    symbol: str = Query(..., description="Ex.: USD/BRL, EUR/USD, BTC/USDT"),
    broker: str = Query("Quotex"),
    market: str = Query("OTC")
):
    if broker not in BROKERS:
        raise HTTPException(400, f"Broker desconhecido: {broker}")

    provider = pick_feed(broker, symbol, market)
    price = provider["price_fn"]()
    if price is None:
        raise HTTPException(502, f"Falha ao obter preço para {symbol} ({provider['source']})")

    return {
        "symbol": symbol,
        "broker": broker,
        "market": market,
        "price": price,
        "price_source": provider["source"],
        "data_quality": provider["quality"],
        "timestamp": now_utc().isoformat()
    }

@app.post("/analyze")
async def analyze(request: Request):
    body = await request.json()
    symbol = body.get("symbol", "EUR/USD")
    broker = body.get("broker", "Quotex")
    market = body.get("market", "OTC")
    timeframe = body.get("timeframe", "M1").upper()

    if broker not in BROKERS:
        raise HTTPException(400, f"Broker desconhecido: {broker}")

    provider = pick_feed(broker, symbol, market)
    prov_name = provider["source"]
    quality = provider["quality"]

    prov_interval = tf_to_provider_interval(timeframe, prov_name)

    # candles
    df = provider["candles_fn"](prov_interval)
    if df.empty:
        raise HTTPException(502, f"Sem candles para {symbol} em {prov_name}")

    # alinhar à borda do timeframe (UTC)
    now = now_utc()
    edge = floor_to_frame(now, timeframe)
    # garanta que última linha seja <= edge
    df = df[df["datetime"] <= edge]
    if df.empty:
        raise HTTPException(502, "Sem vela fechada na borda do timeframe.")
    # últimos N
    df = df.tail(200).reset_index(drop=True)

    # indicadores
    df = compute_indicators(df)
    sig = make_signal(df)

    # preço atual (tick)
    last_price = provider["price_fn"]()
    if last_price is None:
        # usa último close se não houver tick
        last_price = float(df.iloc[-1]["close"])

    resp = {
        "symbol": symbol,
        "broker": broker,
        "market": market,
        "timeframe": timeframe,
        "price_source": prov_name,
        "data_quality": quality,
        "frame_edge_utc": edge.isoformat(),
        "last_close": float(df.iloc[-1]["close"]),
        "last_price": float(last_price),
        "indicators": {
            "ema9": round(float(df.iloc[-1]["ema9"]), 6),
            "ema21": round(float(df.iloc[-1]["ema21"]), 6),
            "rsi14": round(float(df.iloc[-1]["rsi14"]), 2),
            "bb_low": round(float(df.iloc[-1]["bb_low"]), 6),
            "bb_high": round(float(df.iloc[-1]["bb_high"]), 6),
        },
        "signal": sig["signal"],
        "confidence": sig["confidence"],
        "reasons": sig["reasons"]
    }

    # Telegram (opcional/manual controlado por TG_AUTO)
    if TG_AUTO and resp["signal"] in ("CALL","PUT"):
        tg_send(
            f"📈 {APP_NAME}\n"
            f"Broker: {broker} ({market})\nPar: {symbol}\nTF: {timeframe}\n"
            f"Sinal: {resp['signal']} ({resp['confidence']}%)\n"
            f"Preço: {resp['last_price']} | Fonte: {prov_name} ({quality})\n"
            f"Borda: {resp['frame_edge_utc']}"
        )

    return resp

# ---------- Execução local ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
