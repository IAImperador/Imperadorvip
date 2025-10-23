from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import requests
import pandas as pd
import ta
import os

app = FastAPI()

# ==================================
# CONFIGURAÇÃO CORS
# ==================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================================
# VARIÁVEIS DE AMBIENTE
# ==================================
TWELVEDATA_KEY = os.getenv("TWELVEDATA_KEY", "")
API_KEY = os.getenv("API_KEY", "imperadorvip-secure-key-2025")

# ==================================
# ROTA PRINCIPAL DE STATUS
# ==================================
@app.get("/")
def root():
    return {"status": "Imperador API ativa com sucesso!"}

# ==================================
# ROTA DE ANÁLISE
# ==================================
@app.post("/analyze")
async def analyze(request: Request):
    try:
        data = await request.json()
        symbol = data.get("symbol", "EUR/USD")
        interval = data.get("interval", "1min")

        # Consulta à API TwelveData
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize=50&apikey={TWELVEDATA_KEY}"
        response = requests.get(url)
        json_data = response.json()

        # Se a resposta estiver OK
        if "values" in json_data:
            df = pd.DataFrame(json_data["values"])
            df = df.astype(float, errors="ignore")
            df = df.iloc[::-1]  # inverter ordem

            # Adiciona indicadores técnicos
            df["rsi"] = ta.momentum.RSIIndicator(df["close"]).rsi()
            df["ema_fast"] = ta.trend.EMAIndicator(df["close"], window=9).ema_indicator()
            df["ema_slow"] = ta.trend.EMAIndicator(df["close"], window=21).ema_indicator()
            df["macd"] = ta.trend.MACD(df["close"]).macd()

            # Último candle
            latest = df.iloc[-1].to_dict()
            signal = None

            if latest["rsi"] < 30 and latest["ema_fast"] > latest["ema_slow"]:
                signal = "CALL"
            elif latest["rsi"] > 70 and latest["ema_fast"] < latest["ema_slow"]:
                signal = "PUT"
            else:
                signal = "NEUTRO"

            return {
                "status": "ok",
                "symbol": symbol,
                "price": latest["close"],
                "signal": signal,
                "rsi": latest["rsi"],
                "ema_fast": latest["ema_fast"],
                "ema_slow": latest["ema_slow"],
                "macd": latest["macd"],
            }
        else:
            return {"detail": f"400: Falha ao consultar TwelveData: {json_data}"}

    except Exception as e:
        return {"detail": f"Erro na análise: {str(e)}"}

# ==================================
# ROTAS DE BOT (placeholders)
# ==================================
@app.post("/bot/config")
async def bot_config(request: Request):
    data = await request.json()
    return {"status": "config recebido", "data": data}

@app.post("/bot/enable")
async def bot_enable():
    return {"status": "Bot ativado com sucesso"}

@app.post("/bot/disable")
async def bot_disable():
    return {"status": "Bot desativado com sucesso"}

