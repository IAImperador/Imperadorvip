import os
import json
import math
from typing import Optional, Dict, Any

import numpy as np
import pandas as pd
import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

# ==========
# Config
# ==========
API_KEY = os.getenv("API_KEY", "imperadorvip-secure-key-2025")

TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY") or os.getenv("TWELVEDATA_KEY")  # aceita ambos
TWELVEDATA_BASE = "https://api.twelvedata.com"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
AUTO_BOT_ENABLED = False  # alternado via endpoints

# memória de runtime para permitir override via /bot/config
runtime_cfg: Dict[str, Any] = {
    "TELEGRAM_TOKEN": TELEGRAM_TOKEN,
    "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID,
    "AUTO_BOT_ENABLED": AUTO_BOT_ENABLED,
}

# ==========
# FastAPI
# ==========
app = FastAPI(title="IA do Imperador", version="1.0.0")


# ==========
# Utils
# ==========
def require_api_key(x_api_key: Optional[str]):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")


def clean_symbol(symbol: str) -> str:
    s = symbol.strip().upper()
    # normalizações simples comuns
    s = s.replace(" ", "")
    return s


async def fetch_twelvedata_series(symbol: str, interval: str, limit: int = 200) -> pd.DataFrame:
    api_key = (runtime_cfg.get("TWELVEDATA_API_KEY") or TWELVEDATA_API_KEY)
    if not api_key:
        raise HTTPException(status_code=400, detail="Falta TWELVEDATA_KEY")

    params = {
        "symbol": symbol,           # ex: "EUR/USD"
        "interval": interval,       # ex: "1min"
        "outputsize": limit,
        "apikey": api_key,
        "format": "JSON",
        "dp": "5",
        "order": "ASC",
    }

    url = f"{TWELVEDATA_BASE}/time_series"
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(url, params=params)
    if r.status_code != 200:
        raise HTTPException(status_code=400, detail=f"TwelveData HTTP {r.status_code}")

    data = r.json()
    if "values" not in data:
        # resposta de erro do provider
        raise HTTPException(status_code=400, detail="400: Falha ao consultar TwelveData")

    # monta DataFrame
    rows = data["values"]
    df = pd.DataFrame(rows)
    # garante tipos
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    return df


def ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def rsi(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    up = np.where(delta > 0, delta, 0.0)
    down = np.where(delta < 0, -delta, 0.0)
    roll_up = pd.Series(up).ewm(alpha=1/length, adjust=False).mean()
    roll_down = pd.Series(down).ewm(alpha=1/length, adjust=False).mean()
    rs = roll_up / (roll_down + 1e-12)
    rsi_val = 100 - (100 / (1 + rs))
    return pd.Series(rsi_val, index=close.index)


def mk_signal(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Confluência simples e transparente:
    - Direção por EMAs (9, 21)
    - RSI para sobrecompra/sobrevenda
    - Confiança ponderada e limitada (não promete 99%)
    """
    close = df["close"]
    ema9 = ema(close, 9)
    ema21 = ema(close, 21)
    rsi14 = rsi(close, 14)

    last = df.iloc[-1]
    last_close = float(last["close"])
    last_ema9 = float(ema9.iloc[-1])
    last_ema21 = float(ema21.iloc[-1])
    last_rsi = float(rsi14.iloc[-1])

    # tendência
    trend_up = last_ema9 > last_ema21
    trend_down = last_ema9 < last_ema21

    # confluências
    score = 0.0
    reasons = []

    if trend_up:
        score += 0.35
        reasons.append("EMA9 acima da EMA21 (tendência de alta)")
    elif trend_down:
        score += 0.35
        reasons.append("EMA9 abaixo da EMA21 (tendência de baixa)")

    # RSI
    if last_rsi < 35:
        score += 0.25
        reasons.append("RSI abaixo de 35 (sobrevendido)")
    elif last_rsi > 65:
        score += 0.25
        reasons.append("RSI acima de 65 (sobrecomprado)")

    # candle momentum simples
    body = abs(df["close"].iloc[-1] - df["open"].iloc[-1])
    rng = max(df["high"].iloc[-1] - df["low"].iloc[-1], 1e-6)
    mmt = float(np.clip(body / rng, 0.0, 1.0))
    score += 0.20 * mmt
    reasons.append(f"Momentum do candle: {mmt:.2f}")

    # volatilidade moderada favorece sinais
    vol = float(np.clip(df["close"].pct_change().rolling(10).std().iloc[-1] * 100, 0.0, 3.0))
    # quanto mais próximo de ~0.6%–1.2%, melhor (heurística leve)
    if 0.6 <= vol <= 1.2:
        score += 0.10
        reasons.append("Volatilidade saudável")
    else:
        reasons.append("Volatilidade fora do ideal")

    # clamp e direção final
    score = float(np.clip(score, 0.05, 0.92))  # nunca 99% – evita falsa expectativa
    direction = "CALL" if trend_up and last_rsi < 65 else "PUT" if trend_down and last_rsi > 35 else ("CALL" if mmt >= 0.5 else "PUT")

    return {
        "price": last_close,
        "signal": direction,
        "confidence": round(score * 100, 1),
        "rsi": round(last_rsi, 2),
        "ema9": round(last_ema9, 5),
        "ema21": round(last_ema21, 5),
        "reasons": reasons,
    }


async def telegram_send(text: str) -> bool:
    token = runtime_cfg.get("TELEGRAM_TOKEN") or TELEGRAM_TOKEN
    chat_id = runtime_cfg.get("TELEGRAM_CHAT_ID") or TELEGRAM_CHAT_ID
    if not token or not chat_id:
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(url, json=payload)
    return r.status_code == 200


# ==========
# Schemas
# ==========
class AnalyzeIn(BaseModel):
    symbol: str = "EUR/USD"
    interval: str = "1min"
    auto_send: Optional[bool] = False


class BotConfigIn(BaseModel):
    telegram_token: Optional[str] = None
    chat_id: Optional[str] = None
    twelvedata_key: Optional[str] = None


# ==========
# Endpoints
# ==========
@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/price/{symbol}")
async def price(symbol: str):
    """
    Endpoint simples pra consumir preço atual pelo front (se quiser).
    """
    s = clean_symbol(symbol)
    df = await fetch_twelvedata_series(s, "1min", 5)
    last = float(df["close"].iloc[-1])
    return {"symbol": s, "price": last}


@app.post("/analyze")
async def analyze(body: AnalyzeIn, x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)

    symbol = clean_symbol(body.symbol)
    try:
        df = await fetch_twelvedata_series(symbol, body.interval, 200)
    except HTTPException as e:
        raise e
    except Exception:
        raise HTTPException(status_code=400, detail="400: Falha ao consultar TwelveData")

    if len(df) < 30:
        raise HTTPException(status_code=422, detail="Dados insuficientes")

    sig = mk_signal(df)

    # envio automático opcional
    if body.auto_send and (runtime_cfg.get("AUTO_BOT_ENABLED") is True):
        text = (
            f"👑 <b>IA do Imperador</b>\n"
            f"Ativo: <b>{symbol}</b>\n"
            f"Sinal: <b>{sig['signal']}</b> ({sig['confidence']}%)\n"
            f"RSI: {sig['rsi']} | EMA9: {sig['ema9']} | EMA21: {sig['ema21']}\n"
        )
        await telegram_send(text)

    return {"symbol": symbol, "interval": body.interval, "result": sig}


@app.post("/bot/config")
async def bot_config(cfg: BotConfigIn, x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)

    if cfg.telegram_token is not None:
        runtime_cfg["TELEGRAM_TOKEN"] = cfg.telegram_token.strip()

    if cfg.chat_id is not None:
        runtime_cfg["TELEGRAM_CHAT_ID"] = cfg.chat_id.strip()

    if cfg.twelvedata_key is not None:
        runtime_cfg["TWELVEDATA_API_KEY"] = cfg.twelvedata_key.strip()

    return {"ok": True, "config": {
        "TELEGRAM_TOKEN": bool(runtime_cfg.get("TELEGRAM_TOKEN")),
        "TELEGRAM_CHAT_ID": runtime_cfg.get("TELEGRAM_CHAT_ID"),
        "TWELVEDATA_API_KEY": "***" if runtime_cfg.get("TWELVEDATA_API_KEY") else None
    }}


@app.post("/bot/enable")
async def bot_enable(x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    runtime_cfg["AUTO_BOT_ENABLED"] = True
    return {"enabled": True}


@app.post("/bot/disable")
async def bot_disable(x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    runtime_cfg["AUTO_BOT_ENABLED"] = False
    return {"enabled": False}


@app.get("/bot/status")
async def bot_status(x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    return {
        "enabled": bool(runtime_cfg.get("AUTO_BOT_ENABLED")),
        "has_token": bool(runtime_cfg.get("TELEGRAM_TOKEN") or TELEGRAM_TOKEN),
        "chat_id": runtime_cfg.get("TELEGRAM_CHAT_ID") or TELEGRAM_CHAT_ID,
    }
