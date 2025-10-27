from fastapi import FastAPI, Body
import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ImperadorVIP Signals API")

# Variáveis globais
BOT_ACTIVE = False
LAST_SIGNAL = {}

@app.get("/")
def home():
    return {"status": "ok", "service": "ImperadorVIP Signals API", "time": time.strftime("%Y-%m-%dT%H:%M:%S")}

@app.get("/health")
def health_check():
    return {"status": "ok", "msg": "API funcional"}

@app.get("/signal/live")
def get_signal():
    if not LAST_SIGNAL:
        return {"detail": "Nenhum sinal disponível ainda"}
    return {"status": "ok", "sinal": LAST_SIGNAL}

# ---------------------------
# ROTA /analyze (TwelveData)
# ---------------------------
@app.post("/analyze")
def analisar_sinal(data: dict = Body(...)):
    try:
        symbol = data.get("symbol", "EUR/USD").replace("/", "")
        interval = data.get("interval", "1min")

        api_key = os.getenv("TWELVEDATA_KEY")
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize=30&apikey={api_key}"
        response = requests.get(url)
        response.raise_for_status()
        data_api = response.json()

        if "values" not in data_api:
            return {"detail": "Erro na API TwelveData", "data": data_api}

        close_prices = [float(v["close"]) for v in data_api["values"][:5]]
        direction = "CALL" if close_prices[0] < close_prices[-1] else "PUT"

        confidence = round(abs((close_prices[-1] - close_prices[0]) / close_prices[0]) * 100, 2)
        if confidence < 90:
            direction = "NEUTRO"

        LAST_SIGNAL.update({
            "ativo": symbol,
            "sinal": direction,
            "confianca": confidence
        })

        return {"status": "ok", "sinal": LAST_SIGNAL}

    except Exception as e:
        return {"detail": f"Erro interno: {str(e)}"}

# ---------------------------
# ROTA /bot/status
# ---------------------------
@app.post("/bot/status")
def alternar_bot(body: dict = Body(...)):
    """Ativa ou desativa o bot de envio automático"""
    global BOT_ACTIVE
    BOT_ACTIVE = body.get("ativo", False)
    return {"bot_status": BOT_ACTIVE, "msg": "Bot atualizado com sucesso"}
