from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio, httpx, os, json, datetime, random

app = FastAPI(title="IA do Imperador - Live Signals")

# ============= CORS LIBERADO =============
origins = [
    "https://imperadorvip-production.up.railway.app",
    "https://imperadorvip.base44.app",
    "https://app.base44.io",
    "*"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= VARIÁVEIS .ENV =============
API_KEY = os.getenv
# ==========================
# 🔥 ROTA /signal/live — IA do Imperador
# ==========================
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import aiohttp, asyncio, os, time
from datetime import datetime

app = FastAPI()

# CORS
origins = [
    "https://app.base44.io",
    "https://imperadorvip.base44.app",
    "https://imperadorvip-production.up.railway.app",
    "*",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")
SYMBOL = "EUR/USD"
INTERVAL = "1min"
MIN_CONFIDENCE = 90  # filtro de mínima confiança
SIGNAL_CACHE = {"last": None, "confidence": 0}


async def get_price_data():
    """Consulta dados reais da TwelveData"""
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={INTERVAL}&apikey={TWELVEDATA_API_KEY}&outputsize=5"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=400, detail="Falha ao consultar TwelveData")
            data = await resp.json()
            if "values" not in data:
                raise HTTPException(status_code=404, detail="Sem dados válidos da API")
            return data["values"]


def analyze_signal(values):
    """Analisa tendência e retorna sinal e confiança"""
    last = float(values[0]["close"])
    prev = float(values[1]["close"])
    diff = last - prev

    # Exemplo simples de confiança
    confidence = min(99, abs(diff) * 1000)

    if confidence < MIN_CONFIDENCE:
        return None, confidence

    if diff > 0:
        return "CALL", confidence
    elif diff < 0:
        return "PUT", confidence
    else:
        return None, confidence


@app.get("/signal/live")
async def signal_live():
    """Gera sinal ao vivo a cada 60s"""
    try:
        values = await get_price_data()
        signal, confidence = analyze_signal(values)
        SIGNAL_CACHE["last"] = signal
        SIGNAL_CACHE["confidence"] = confidence

        if signal:
            return {
                "status": "ok",
                "timestamp": datetime.utcnow().isoformat(),
                "signal": signal,
                "confidence": confidence,
                "pair": SYMBOL,
            }
        else:
            return {
                "status": "no_signal",
                "confidence": confidence,
                "message": "Sem sinal acima do limite mínimo"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
