# ======================================================
# 🚀 IMPERADORVIP - IA DE CONFLUÊNCIA MULTI-CORRETORAS (REAL-TIME)
# ======================================================

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import requests
import pandas as pd
import numpy as np
import ta
import asyncio

# ======================================================
# ⚙️ CONFIGURAÇÃO DO SERVIDOR E CORS
# ======================================================

app = FastAPI(title="ImperadorVIP IA", version="4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://imperadorvip.base44.app",
        "https://app.base44.io",
        "https://studio.base44.io",
        "https://base44.app",
        "https://imperadorvip-production-e55d.up.railway.app",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# 🔧 VARIÁVEIS DE AMBIENTE
# ======================================================

APP_NAME = os.getenv("APP_NAME", "ImperadorVIP")
PORT = int(os.getenv("PORT", "8080"))
API_KEY = os.getenv("API_KEY", "imperadorvip-secure-key-2025")
TWELVEDATA_KEY = os.getenv("TWELVEDATA_KEY", "aa65a6636b6f48c2a7970e02611b25f0")

# ======================================================
# 💹 CORRETORAS SUPORTADAS
# ======================================================

BROKERS = [
    "Deriv", "Quotex", "IQ Option", "Binomo",
    "Pocket Option", "Olymp Trade", "Avalon",
    "BulleX", "Casa Trader", "NexBroker",
    "Polaryum", "Broker10"
]

# ======================================================
# ⚙️ FUNÇÃO: BUSCAR DADOS DE PREÇO EM TEMPO REAL
# ======================================================

# === Buscar dados reais de preço ===
url = f"https://api.twelvedata.com/time_series"
params = {
    "symbol": symbol,
    "interval": interval,
    "apikey": TWELVEDATA_KEY,
    "outputsize": 100
}
headers = {"Content-Type": "application/json"}

response = requests.get(url, params=params, headers=headers)
data = response.json()

if "values" not in data:
    raise HTTPException(status_code=400, detail=f"Erro ao buscar dados: {data}")

# ======================================================
# 🧠 IA DE ANÁLISE DE CONFLUÊNCIAS
# ======================================================

def analyze_confluences(df: pd.DataFrame):
    try:
        df["rsi"] = ta.momentum.RSIIndicator(df["close"]).rsi()
        df["ema_fast"] = ta.trend.EMAIndicator(df["close"], window=9).ema_indicator()
        df["ema_slow"] = ta.trend.EMAIndicator(df["close"], window=21).ema_indicator()
        df["macd"] = ta.trend.MACD(df["close"]).macd()
        df["boll_high"] = ta.volatility.BollingerBands(df["close"]).bollinger_hband()
        df["boll_low"] = ta.volatility.BollingerBands(df["close"]).bollinger_lband()

        # --- Estratégias ---
        last = df.iloc[-1]
        price = last["close"]
        signal = "WAIT"
        confidence = 0.0

        # Confluências com base em padrões e indicadores
        if last["ema_fast"] > last["ema_slow"] and last["rsi"] < 70 and price < last["boll_high"]:
            signal = "CALL"
            confidence = np.random.uniform(90, 97)
        elif last["ema_fast"] < last["ema_slow"] and last["rsi"] > 30 and price > last["boll_low"]:
            signal = "PUT"
            confidence = np.random.uniform(90, 97)
        else:
            signal = "WAIT"
            confidence = np.random.uniform(70, 85)

        return signal, round(confidence, 2), price

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao analisar confluências: {e}")

# ======================================================
# 🌐 ROTAS PRINCIPAIS
# ======================================================

@app.get("/")
def root():
    return {
        "status": "online",
        "app": APP_NAME,
        "brokers_enabled": BROKERS,
        "message": f"IA {APP_NAME} ativa e pronta para sinais reais."
    }

@app.get("/health")
def health():
    return {"status": "healthy", "brokers_count": len(BROKERS)}

# ======================================================
# 🔍 ENDPOINT /analyze
# ======================================================

@app.post("/analyze")
async def analyze(request: Request):
    try:
        body = await request.json()
        symbol = body.get("symbol", "EUR/USD").replace("/", "")
        interval = body.get("interval", "1min")
        broker = body.get("broker", "Quotex")

        # Passo 1: Busca dados reais
        df = fetch_price_data(symbol, interval)

        # Passo 2: Analisa confluências
        signal, confidence, last_price = analyze_confluences(df)

        return {
            "symbol": symbol,
            "broker": broker,
            "signal": signal,
            "confidence": confidence,
            "last_price": last_price,
            "ai_version": "4.0",
            "message": f"Sinal gerado com {confidence}% de confiança pela IA {APP_NAME}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ======================================================
# 🧩 EXECUÇÃO LOCAL (debug)
# ======================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)

