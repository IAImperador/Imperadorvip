from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
import pandas as pd
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

# ============================
# CONFIGURAÇÃO DO APP
# ============================
app = FastAPI()
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("API_KEY", "imperadorvip-secure-key-2025")
TWELVEDATA_KEY = os.getenv("TWELVEDATA_KEY", "aa65a6636b6f48c2a7970e02611b25f0")

# ============================
# ROTA DE STATUS
# ============================
@app.get("/")
def root():
    return {"status": "✅ API do Imperador operacional"}

# ============================
# ROTA DE ANÁLISE TWELVEDATA
# ============================
@app.post("/analyze")
async def analyze(request: Request):
    try:
        body = await request.json()
        symbol = body.get("symbol", "EUR/USD").replace("/", "")
        interval = body.get("interval", "1min")

        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&apikey={TWELVEDATA_KEY}&outputsize=50"
        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Erro HTTP {r.status_code} ao consultar TwelveData")

        data = r.json()

        if "values" not in data:
            raise HTTPException(status_code=400, detail=f"400: Falha ao consultar TwelveData: {data.get('message', 'Sem dados retornados')}")

        df = pd.DataFrame(data["values"])
        df["close"] = df["close"].astype(float)
        df = df.sort_values("datetime")

        # Indicadores técnicos
        df["ema_9"] = EMAIndicator(df["close"], window=9).ema_indicator()
        df["ema_21"] = EMAIndicator(df["close"], window=21).ema_indicator()
        df["rsi"] = RSIIndicator(df["close"], window=14).rsi()
        macd = MACD(df["close"])
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        boll = BollingerBands(df["close"])
        df["bb_high"] = boll.bollinger_hband()
        df["bb_low"] = boll.bollinger_lband()

        ultima = df.iloc[-1]

        # Interpretação básica da tendência
        tendencia = (
            "Alta forte" if ultima["ema_9"] > ultima["ema_21"] and ultima["rsi"] < 70 else
            "Baixa forte" if ultima["ema_9"] < ultima["ema_21"] and ultima["rsi"] > 30 else
            "Lateralização"
        )

        return {
            "symbol": symbol,
            "interval": interval,
            "price": ultima["close"],
            "tendencia": tendencia,
            "rsi": round(float(ultima["rsi"]), 2),
            "ema_9": round(float(ultima["ema_9"]), 5),
            "ema_21": round(float(ultima["ema_21"]), 5),
            "macd": round(float(ultima["macd"]), 5),
            "macd_signal": round(float(ultima["macd_signal"]), 5),
            "bb_high": round(float(ultima["bb_high"]), 5),
            "bb_low": round(float(ultima["bb_low"]), 5),
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Falha ao consultar TwelveData: {str(e)}")

# ============================
# BOT TELEGRAM (PLACEHOLDERS)
# ============================
@app.post("/bot/config")
async def bot_config(request: Request):
    data = await request.json()
    return {"status": "ok", "config": data}

@app.post("/bot/enable")
def bot_enable():
    return {"status": "ok", "message": "Bot ativado"}

@app.post("/bot/disable")
def bot_disable():
    return {"status": "ok", "message": "Bot desativado"}

# ============================
# RODAR LOCAL (Railway faz automaticamente)
# ============================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


