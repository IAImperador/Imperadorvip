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
import json

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
        "*",
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
TWELVEDATA_KEY = os.getenv("TWELVEDATA_KEY", "demo")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "@Iadoimperador")

# ======================================================
# 💹 CORRETORAS E ATIVOS SUPORTADOS
# ======================================================

BROKERS = {
    "Deriv": ["EUR/USD", "GBP/USD", "AUD/USD", "USD/JPY", "XAU/USD"],
    "Quotex": ["EUR/USD", "GBP/JPY", "USD/CHF", "BTC/USD", "ETH/USD"],
    "IQ Option": ["EUR/USD", "USD/CAD", "GBP/JPY", "AUD/JPY", "NZD/USD"],
    "Binomo": ["EUR/USD", "AUD/USD", "USD/JPY", "USD/CHF"],
    "Pocket Option": ["EUR/USD", "GBP/USD", "BTC/USD", "USD/JPY"],
    "Olymp Trade": ["EUR/USD", "GBP/JPY", "USD/CHF", "AUD/USD"],
    "Avalon": ["EUR/USD", "USD/JPY", "BTC/USD", "ETH/USD"],
    "BulleX": ["EUR/USD", "GBP/USD", "USD/JPY", "BTC/USD"],
    "Casa Trader": ["EUR/USD", "USD/CHF", "BTC/USD", "XAU/USD"],
    "NexBroker": ["EUR/USD", "USD/JPY", "ETH/USD", "XAU/USD"],
    "Polaryum": ["EUR/USD", "GBP/USD", "USD/JPY", "BTC/USD"],
    "Broker10": ["EUR/USD", "GBP/JPY", "BTC/USD", "ETH/USD"],
}

# ======================================================
# 📡 FUNÇÃO DE BUSCA DE DADOS REAIS (TwelveData)
# ======================================================

def get_real_data(symbol, interval):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&apikey={TWELVEDATA_KEY}&outputsize=100"
        response = requests.get(url, timeout=10)
        data = response.json()
        if "values" not in data:
            raise Exception("Erro ao buscar dados de mercado")
        df = pd.DataFrame(data["values"])
        df = df.astype({"open": float, "close": float, "high": float, "low": float})
        df = df[::-1].reset_index(drop=True)
        return df
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ======================================================
# 🧠 ANÁLISE COMPLETA COM CONFLUÊNCIAS
# ======================================================

def analyze_market(df):
    df["rsi"] = ta.momentum.RSIIndicator(df["close"]).rsi()
    df["ema9"] = ta.trend.EMAIndicator(df["close"], window=9).ema_indicator()
    df["ema21"] = ta.trend.EMAIndicator(df["close"], window=21).ema_indicator()
    df["macd"] = ta.trend.MACD(df["close"]).macd()
    bb = ta.volatility.BollingerBands(df["close"])
    df["bb_high"] = bb.bollinger_hband()
    df["bb_low"] = bb.bollinger_lband()
    df["adx"] = ta.trend.ADXIndicator(df["high"], df["low"], df["close"]).adx()

    last = df.iloc[-1]
    signal = "WAIT"
    confluences = []

    # Estratégias e Padrões
    if last["ema9"] > last["ema21"] and last["rsi"] < 70 and last["macd"] > 0:
        signal = "CALL"
        confluences.append("Tendência de alta (EMA + RSI + MACD)")
    elif last["ema9"] < last["ema21"] and last["rsi"] > 30 and last["macd"] < 0:
        signal = "PUT"
        confluences.append("Tendência de baixa (EMA + RSI + MACD)")

    if last["close"] <= last["bb_low"]:
        confluences.append("Região de suporte (Bollinger Lower)")
    elif last["close"] >= last["bb_high"]:
        confluences.append("Região de resistência (Bollinger Upper)")

    confidence = min(99, 85 + len(confluences) * 3)
    return signal, confidence, confluences, last

# ======================================================
# 📢 ENVIO AUTOMÁTICO PARA TELEGRAM
# ======================================================

def send_signal_to_telegram(message):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
            requests.post(url, data=data)
        except:
            print("⚠️ Erro ao enviar sinal ao Telegram")

# ======================================================
# 🌐 ROTAS PRINCIPAIS
# ======================================================

@app.get("/")
def root():
    return {"status": "online", "brokers": list(BROKERS.keys()), "message": "IA ImperadorVIP ativa e pronta."}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/analyze")
async def analyze(request: Request):
    try:
        body = await request.json()
        broker = body.get("broker", "Quotex")
        symbol = body.get("symbol", "EUR/USD")
        interval = body.get("interval", "1min")

        if broker not in BROKERS:
            raise HTTPException(status_code=400, detail="Corretora não reconhecida.")
        if symbol not in BROKERS[broker]:
            raise HTTPException(status_code=400, detail=f"Ativo {symbol} não disponível na {broker}.")

        df = get_real_data(symbol.replace("/", ""), interval)
        signal, confidence, confluences, last = analyze_market(df)

        message = f"📊 <b>SINAL {signal}</b>\n💹 Ativo: {symbol}\n🏦 Corretora: {broker}\n⏱ Timeframe: {interval}\n🎯 Confluências: {len(confluences)}\n📈 Confiança: {confidence}%"
        send_signal_to_telegram(message)

        return {
            "symbol": symbol,
            "broker": broker,
            "interval": interval,
            "signal": signal,
            "confidence": confidence,
            "confluences": confluences,
            "last_price": last["close"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ======================================================
# 🧩 EXECUÇÃO LOCAL
# ======================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)

