from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.analysis import analyze_signal
import os

app = FastAPI(title="IA do Imperador", version="4.0")

# Libera acesso à Base44
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "ok", "service": "ImperadorVIP Signals API"}

@app.get("/analyze")
def analyze(pair: str = "EUR/USD", timeframe: str = "M5", market: str = "OTC"):
    result = analyze_signal(pair, timeframe, market)
    return {"pair": pair, "timeframe": timeframe, "market": market, "result": result}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
