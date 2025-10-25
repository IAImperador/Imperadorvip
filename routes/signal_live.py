from fastapi import APIRouter
import requests
import os
from datetime import datetime
import random

signal_live_router = APIRouter()

TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY", "")
SYMBOL = "EUR/USD"  # pode alterar depois
INTERVAL = "1min"
MIN_CONFIDENCE = 90.0  # só envia sinais acima disso

@signal_live_router.get("/signal/live")
async def signal_live():
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={INTERVAL}&apikey={TWELVEDATA_API_KEY}&outputsize=5"
        response = requests.get(url)
        data = response.json()

        if "values" not in data:
            return {"status": "erro", "detail": "Sem dados da TwelveData", "data": data}

        # Extrai últimos preços
        candles = data["values"]
        latest = float(candles[0]["close"])
        prev = float(candles[1]["close"])

        # Cálculo de tendência básica
        if latest > prev:
            sinal = "CALL"
        elif latest < prev:
            sinal = "PUT"
        else:
            sinal = "NEUTRO"

        # Simulação de confiança (ou use seu cálculo real)
        confianca = round(random.uniform(80, 99.9), 2)

        # Filtro: só envia sinais com confiança >= limite
        if confianca < MIN_CONFIDENCE:
            return {"status": "aguardando", "sinal": {"sinal": "NEUTRO", "confianca": confianca}}

        return {
            "status": "ativo",
            "sinal": {
                "par": SYMBOL,
                "direcao": sinal,
                "confianca": confianca,
                "horario": datetime.now().strftime("%H:%M:%S"),
            }
        }

    except Exception as e:
        return {"status": "erro", "detail": str(e)}

