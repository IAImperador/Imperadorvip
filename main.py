import os
from typing import Optional, Dict, Any
from datetime import datetime

import httpx
import numpy as np
import pandas as pd
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# ====== Env ======
load_dotenv()

API_KEY = os.getenv("API_KEY", "imperadorvip-secure-key-2025")
TWELVEDATA_KEY = os.getenv("TWELVEDATA_KEY", "")
APP_NAME = os.getenv("APP_NAME", "ImperadorVIP")
MODE = os.getenv("MODE", "production")
BOT_ACTIVE_DEFAULT = os.getenv("BOT_ACTIVE", "false").lower() == "true"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Estado em memória (reset a cada deploy)
STATE: Dict[str, Any] = {
    "bot_active": BOT_ACTIVE_DEFAULT,
    "telegram": {
        "token": TELEGRAM_BOT_TOKEN or None,
        "chat_id": TELEGRAM_CHAT_ID or None,
    }
}

# ====== App ======
app = FastAPI(title=APP_NAME)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in allowed_origins.split(",")] if allowed_origins else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====== Schemas ======
class AnalyzeInput(BaseModel):
    symbol: str = "EUR/USD"
    interval: str = "1min"

class BotConfig(BaseModel):
    telegram_token: Optional[str] = None
    chat_id: Optional[str] = None

# ====== Utils ======
def require_key(x_api_key: Optional[str]):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

def td_symbol_fix(symbol: str) -> str:
    # TwelveData usa "EUR/USD" → "EUR/USD" mesmo; se vier "EURUSD" normaliza
    if "/" not in symbol and len(symbol) == 6:
        return f"{symbol[:3]}/{symbol[3:]}"
    return symbol

async def fetch_twelvedata(symbol: str, interval: str) -> pd.DataFrame:
    if not TWELVEDATA_KEY:
        raise HTTPException(status_code=400, detail="Falta TWELVEDATA_KEY")

    base = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": td_symbol_fix(symbol),
        "interval": interval,
        "apikey": TWELVEDATA_KEY,
        "outputsize": 100,     # dá para ajustar
        "format": "JSON",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(base, params=params)
    if r.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Falha TwelveData HTTP {r.status_code}")

    data = r.json()
    if data.get("status") != "ok" or "values" not in data:
        raise HTTPException(status_code=400, detail="400: Falha ao consultar TwelveData")

    # Converte para DataFrame
    df = pd.DataFrame(data["values"])
    # garante ordem crescente por datetime
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)

    # preços como float
    for c in ["open", "high", "low", "close"]:
        df[c] = df[c].astype(float)

    return df

def simple_signal_from_df(df: pd.DataFrame) -> Dict[str, Any]:
    # Indicadores simples (RSI / MME)
    close = df["close"].values
    # MME curta e longa
    ema_fast = pd.Series(close).ewm(span=9, adjust=False).mean().values
    ema_slow = pd.Series(close).ewm(span=21, adjust=False).mean().values

    # RSI simplificado
    delta = np.diff(close, prepend=close[0])
    up = np.where(delta > 0, delta, 0.0)
    down = np.where(delta < 0, -delta, 0.0)
    roll_up = pd.Series(up).rolling(14).mean().values
    roll_down = pd.Series(down).rolling(14).mean().values
    rs = np.where(roll_down == 0, np.inf, roll_up / roll_down)
    rsi = 100 - (100 / (1 + rs))

    last_close = close[-1]
    last_rsi = float(np.nan_to_num(rsi[-1], nan=50.0))
    last_ef = float(ema_fast[-1])
    last_es = float(ema_slow[-1])

    # regra:
    # compra se MME9 > MME21 e RSI<70
    # venda se MME9 < MME21 e RSI>30
    # senão neutro
    if last_ef > last_es and last_rsi < 70:
        sig = "CALL"
        conf = min(95, 50 + abs(last_ef - last_es) * 2000)
    elif last_ef < last_es and last_rsi > 30:
        sig = "PUT"
        conf = min(95, 50 + abs(last_ef - last_es) * 2000)
    else:
        sig = "NEUTRO"
        conf = 50

    return {
        "signal": sig,
        "confidence": round(conf, 1),
        "rsi": round(last_rsi, 2),
        "ema_fast": round(last_ef, 6),
        "ema_slow": round(last_es, 6),
        "price": round(last_close, 6),
    }

# ====== Health / Status ======
@app.get("/")
def root():
    return {
        "status": "online",
        "app": APP_NAME,
        "mode": MODE,
        "bot_active": STATE["bot_active"],
        "time": datetime.utcnow().isoformat() + "Z",
    }

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/status")
def status():
    return {
        "ok": True,
        "app": APP_NAME,
        "bot_active": STATE["bot_active"],
        "telegram": STATE["telegram"],
    }

# ====== Bot config ======
@app.post("/bot/config")
def save_bot_config(cfg: BotConfig, x_api_key: Optional[str] = Header(None)):
    require_key(x_api_key)
    if cfg.telegram_token is not None:
        STATE["telegram"]["token"] = cfg.telegram_token or None
    if cfg.chat_id is not None:
        STATE["telegram"]["chat_id"] = cfg.chat_id or None
    return {"ok": True, "telegram": STATE["telegram"]}

@app.post("/bot/enable")
def enable_bot(x_api_key: Optional[str] = Header(None)):
    require_key(x_api_key)
    STATE["bot_active"] = True
    return {"ok": True, "bot_active": True}

@app.post("/bot/disable")
def disable_bot(x_api_key: Optional[str] = Header(None)):
    require_key(x_api_key)
    STATE["bot_active"] = False
    return {"ok": True, "bot_active": False}

# ====== Analyze ======
@app.post("/analyze")
async def analyze(data: AnalyzeInput, x_api_key: Optional[str] = Header(None)):
    require_key(x_api_key)
    df = await fetch_twelvedata(data.symbol, data.interval)
    res = simple_signal_from_df(df)
    return {
        "symbol": td_symbol_fix(data.symbol),
        "interval": data.interval,
        "signal": res["signal"],
        "confidence": res["confidence"],
        "indicators": {
            "rsi": res["rsi"],
            "ema_fast": res["ema_fast"],
            "ema_slow": res["ema_slow"],
        },
        "price": res["price"],
        "sample": len(df),
    }


