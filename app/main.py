from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import os, requests, pandas as pd, numpy as np
from app.indicators import calculate_indicators
from app.strategies import detect_patterns
from app.confluence import calculate_confluence

app = FastAPI(title="ImperadorVIP IA", version="4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

API_KEY = os.getenv("API_KEY", "imperadorvip-secure-key-2025")
TWELVEDATA_KEY = os.getenv("TWELVEDATA_KEY", "")
PORT = int(os.getenv("PORT", 8080))

@app.get("/")
def root():
    return {"status": "ok", "service": "ImperadorVIP Signals API"}

@app.post("/analyze")
async def analyze(request: Request):
    body = await request.json()
    symbol = body.get("symbol", "EUR/USD").replace("/", "")
    interval = body.get("interval", "1min")
    market = body.get("market", "OTC")
    broker = body.get("broker", "Quotex")

    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&apikey={TWELVEDATA_KEY}&outputsize=100"
    resp = requests.get(url)
    data = resp.json()
    if "values" not in data:
        raise HTTPException(status_code=400, detail="Falha ao consultar TwelveData")

    df = pd.DataFrame(data["values"])
    df = df.astype({"open": float, "close": float, "high": float, "low": float})
    df = df[::-1].reset_index(drop=True)

    indicators = calculate_indicators(df)
    pattern = detect_patterns(df)
    confluence, signal = calculate_confluence(indicators, pattern)

    last = df.iloc[-1]
    return {
        "symbol": symbol,
        "broker": broker,
        "market": market,
        "signal": signal,
        "confidence": confluence,
        "price": last["close"],
        "indicators": indicators
    }

@app.post("/signal/live")
async def signal_live():
    symbol = "EUR/USD"
    interval = "1min"
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&apikey={TWELVEDATA_KEY}&outputsize=100"
    resp = requests.get(url)
    data = resp.json()
    if "values" not in data:
        raise HTTPException(status_code=400, detail="Falha ao consultar TwelveData")

    df = pd.DataFrame(data["values"])
    df = df.astype({"open": float, "close": float, "high": float, "low": float})
    df = df[::-1].reset_index(drop=True)

    indicators = calculate_indicators(df)
    pattern = detect_patterns(df)
    confluence, signal = calculate_confluence(indicators, pattern)

    if confluence >= 90:
        return {"signal": signal, "confidence": confluence, "symbol": symbol, "price": df.iloc[-1]["close"]}
    else:
        return {"signal": "WAIT", "confidence": confluence}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True)
