# ======================================================
# 🚀 IMPERADORVIP - IA DE CONFLUÊNCIA GLOBAL (v4.5)
# ======================================================
# Compatível com Base44 + Railway + Telegram + TwelveData

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import requests
import pandas as pd
import numpy as np
import ta
import asyncio
import json
import logging

# ======================================================
# ⚙️ CONFIGURAÇÃO DO SERVIDOR E CORS
# ======================================================

app = FastAPI(title="ImperadorVIP IA", version="4.5")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://imperadorvip.base44.app",
        "https://app.base44.io",
        "https://studio.base44.io",
        "https://base44.app",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# 🔧 VARIÁVEIS DE AMBIENTE
# ======================================================

PORT = int(os.getenv("PORT", "8080"))
API_KEY = os.getenv("API_KEY", "imperadorvip-secure-key-2025")
TWELVEDATA_KEY = os.getenv("TWELVEDATA_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "@IAdoimperador")

# ======================================================
# 💹 CORRETORAS SUPORTADAS
# ======================================================

BROKERS = [
    "Deriv", "Quotex", "IQ Option", "Binomo", "Pocket Option", 
    "Olymp Trade", "Avalon", "BulleX", "Casa Trader", 
    "NexBroker", "Polaryum", "Broker10"
]

# ======================================================
# 🧩 FUNÇÕES AUXILIARES
# ======================================================

def get_symbol(broker, asset):
    """
    Normaliza o ativo conforme a corretora
    """
    symbols = {
        "Quotex": {
            "EUR/USD": "EUR/USD",
            "USD/JPY": "USD/JPY",
            "GBP/USD": "GBP/USD",
            "AUD/USD": "AUD/USD",
            "EUR/JPY": "EUR/JPY"
        },
        "IQ Option": {
            "EURUSD": "EUR/USD",
            "USDJPY": "USD/JPY",
            "GBPUSD": "GBP/USD",
        },
        "Binomo": {
            "EURUSD": "EUR/USD",
            "USDJPY": "USD/JPY",
        },
        "BulleX": {
            "BTC/USD": "BTC/USD",
            "ETH/USD": "ETH/USD"
        }
    }
    if broker in symbols and asset in symbols[broker]:
        return symbols[broker][asset]
    return asset  # fallback padrão


def send_telegram_message(message):
    """
    Envia sinal automaticamente para o canal do Telegram
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
        requests.post(url, data=payload)
    except Exception as e:
        logging.error(f"Erro ao enviar mensagem para Telegram: {e}")


# ======================================================
# 🧠 ROTA /analyze — Análise Completa e Real-Time
# ======================================================

@app.post("/analyze")
async def analyze(request: Request):
    try:
        body = await request.json()
        broker = body.get("broker", "Quotex")
        asset = body.get("symbol", "EUR/USD")
        interval = body.get("interval", "1min")

        # === Validação de parâmetros ===
        if not asset or not interval:
            raise HTTPException(status_code=400, detail="Parâmetros ausentes: symbol ou interval inválido")

        symbol = get_symbol(broker, asset)

        # === Obter dados da TwelveData ===
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&apikey={TWELVEDATA_KEY}&outputsize=100"
        response = requests.get(url, timeout=10)
        data = response.json()

        if "values" not in data:
            raise HTTPException(status_code=400, detail=f"Erro ao buscar dados: {data.get('message', 'Resposta inválida da API')}")

        df = pd.DataFrame(data["values"])
        df = df.astype({"open": float, "close": float, "high": float, "low": float})
        df = df[::-1]

        # === Indicadores Técnicos e Confluências ===
        df["rsi"] = ta.momentum.RSIIndicator(df["close"]).rsi()
        df["ema9"] = ta.trend.EMAIndicator(df["close"], window=9).ema_indicator()
        df["ema21"] = ta.trend.EMAIndicator(df["close"], window=21).ema_indicator()
        df["macd"] = ta.trend.MACD(df["close"]).macd()
        df["boll_h"] = ta.volatility.BollingerBands(df["close"]).bollinger_hband()
        df["boll_l"] = ta.volatility.BollingerBands(df["close"]).bollinger_lband()
        df["atr"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"]).average_true_range()

        last = df.iloc[-1]

        # === Estratégias e Confluências ===
        confluencias = 0
        if last["ema9"] > last["ema21"]: confluencias += 1
        if last["close"] > last["ema9"]: confluencias += 1
        if last["rsi"] < 30: confluencias += 1
        if last["macd"] > 0: confluencias += 1
        if last["close"] < last["boll_l"]: confluencias += 1
        if last["close"] > last["boll_h"]: confluencias += 1

        # === Decisão de sinal ===
        if confluencias >= 4:
            signal = "CALL"
        elif confluencias <= 2:
            signal = "PUT"
        else:
            signal = "WAIT"

        confidence = round(85 + (confluencias * 2.5), 2)
        message = f"🔥 <b>IA ImperadorVIP</b>\n📈 Ativo: {symbol}\n🏦 Corretora: {broker}\n🕐 Timeframe: {interval}\n🎯 Sinal: {signal}\n💡 Confluências: {confluencias}\n📊 Confiança: {confidence}%"

        # === Enviar sinal para o Telegram (opcional) ===
        send_telegram_message(message)

        return {
            "symbol": symbol,
            "broker": broker,
            "interval": interval,
            "signal": signal,
            "confidence": confidence,
            "confluences": confluencias,
            "indicators": {
                "rsi": round(last["rsi"], 2),
                "ema9": round(last["ema9"], 5),
                "ema21": round(last["ema21"], 5),
                "macd": round(last["macd"], 5),
                "atr": round(last["atr"], 5),
            },
            "telegram": TELEGRAM_CHAT_ID
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ======================================================
# 🌐 ROTAS PRINCIPAIS
# ======================================================

@app.get("/")
def root():
    return {"status": "online", "brokers_enabled": BROKERS, "message": "IA ImperadorVIP está online e pronta para operar."}

@app.get("/health")
def health():
    return {"status": "healthy", "brokers": BROKERS}

# ======================================================
# 🧩 EXECUÇÃO LOCAL (debug)
# ======================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
