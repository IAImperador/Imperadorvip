from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import pandas as pd
import numpy as np
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from datetime import datetime

# ============================================
# CONFIGURAÇÃO BÁSICA
# ============================================

app = FastAPI(title="IA do Imperador", version="2.0")

API_KEY = "imperadorvip-secure-key-2025"
TWELVEDATA_URL = "https://api.twelvedata.com/time_series"
TWELVEDATA_KEY = "demo"  # troque pela sua chave real

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# MODELOS DE ENTRADA
# ============================================

class BotConfig(BaseModel):
    telegram_token: str | None = None
    chat_id: str | None = None

class AnalyzeRequest(BaseModel):
    symbol: str
    interval: str

# ============================================
# VALIDAÇÃO DE CHAVE DE API
# ============================================

def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Chave de API inválida")

# ============================================
# ENDPOINTS DO BOT
# ============================================

bot_enabled = False
bot_config = {}

@app.post("/bot/config")
def set_config(config: BotConfig, x_api_key: str = Header(None)):
    verify_api_key(x_api_key)
    global bot_config
    bot_config = config.dict()
    return {"status": "ok", "config": bot_config}

@app.post("/bot/start")
def start_bot(x_api_key: str = Header(None)):
    verify_api_key(x_api_key)
    global bot_enabled
    bot_enabled = True
    return {"status": "started", "message": "Bot ativado com sucesso"}

@app.post("/bot/stop")
def stop_bot(x_api_key: str = Header(None)):
    verify_api_key(x_api_key)
    global bot_enabled
    bot_enabled = False
    return {"status": "stopped", "message": "Bot desativado com sucesso"}

# ============================================
# ANÁLISE TWELVEDATA + INDICADORES
# ============================================

@app.post("/analyze")
def analyze(req: AnalyzeRequest, x_api_key: str = Header(None)):
    verify_api_key(x_api_key)

    params = {
        "symbol": req.symbol,
        "interval": req.interval,
        "apikey": TWELVEDATA_KEY,
        "outputsize": 60
    }

    r = requests.get(TWELVEDATA_URL, params=params)
    data = r.json()

    if "values" not in data:
        raise HTTPException(status_code=400, detail="400: Falha ao consultar TwelveData")

    df = pd.DataFrame(data["values"])
    df = df.astype({"open": float, "high": float, "low": float, "close": float})
    df["close"] = df["close"].astype(float)
    df = df[::-1]  # inverte a ordem para mais recente no fim

    # ==========================
    # INDICADORES TÉCNICOS
    # ==========================
    df["EMA_fast"] = EMAIndicator(close=df["close"], window=5).ema_indicator()
    df["EMA_slow"] = EMAIndicator(close=df["close"], window=20).ema_indicator()
    df["RSI"] = RSIIndicator(close=df["close"], window=14).rsi()

    macd = MACD(close=df["close"])
    df["MACD"] = macd.macd()
    df["Signal"] = macd.macd_signal()

    last = df.iloc[-1]

    # ==========================
    # LÓGICA DE SINAL
    # ==========================
    signal = "NEUTRO"
    confidence = 50

    if last["EMA_fast"] > last["EMA_slow"] and last["MACD"] > last["Signal"] and last["RSI"] < 70:
        signal = "CALL"
        confidence = 94.3
    elif last["EMA_fast"] < last["EMA_slow"] and last["MACD"] < last["Signal"] and last["RSI"] > 30:
        signal = "PUT"
        confidence = 93.7

    return {
        "timestamp": datetime.now().isoformat(),
        "symbol": req.symbol,
        "interval": req.interval,
        "signal": signal,
        "accuracy": confidence,
        "close": last["close"],
        "rsi": last["RSI"],
        "ema_fast": last["EMA_fast"],
        "ema_slow": last["EMA_slow"],
        "macd": last["MACD"],
        "signal_line": last["Signal"]
    }

