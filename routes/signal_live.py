# routes/signal_live.py
from fastapi import APIRouter, BackgroundTasks
import asyncio
import requests
import os
from datetime import datetime

router = APIRouter()

TWELVEDATA_KEY = os.getenv("TWELVEDATA_API_KEY")
SYMBOL = "EUR/USD"
INTERVAL = "1min"
CONFIDENCE_MIN = 90  # só envia sinais com confiança >= 90%

async def fetch_signal():
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={INTERVAL}&apikey={TWELVEDATA_KEY}&outputsize=5"
    response = requests.get(url)
    data = response.json()
    if "values" not in data:
        return None

    last_close = float(data["values"][0]["close"])
    previous_close = float(data["values"][1]["close"])
    direction = "CALL" if last_close > previous_close else "PUT"

    confidence = abs((last_close - previous_close) / previous_close * 100)
    signal = {
        "symbol": SYMBOL,
        "direction": direction,
        "confidence": round(confidence, 2),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    if confidence >= CONFIDENCE_MIN:
        print(f"✅ Sinal enviado: {signal}")
    else:
        print(f"⚠️ Confiança baixa ({confidence:.2f}%), sinal ignorado")

    return signal


@router.get("/signal/live")
async def live_signal(background_tasks: BackgroundTasks):
    """Executa a cada 60s e retorna o último sinal com alta confiança."""
    async def loop_signals():
        while True:
            await fetch_signal()
            await asyncio.sleep(60)

    background_tasks.add_task(loop_signals)
    return {"status": "Sinal ao vivo iniciado", "interval": "60s", "min_confidence": CONFIDENCE_MIN}
