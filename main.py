from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import httpx
import os
from datetime import datetime
import random

# -----------------------------
# Configurações principais
# -----------------------------
app = FastAPI(title="Imperial IA do Imperador — Sinais Live")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")

if not TWELVEDATA_API_KEY:
    raise ValueError("❌ TWELVEDATA_API_KEY não configurada nas variáveis de ambiente!")

# Lista de ativos disponíveis
ASSETS = [
    "EUR/USD", "USD/JPY", "GBP/USD", "AUD/USD", "USD/CAD",
    "USD/CHF", "NZD/USD", "EUR/JPY", "GBP/JPY", "EUR/GBP",
    "EUR/CAD", "AUD/JPY", "CHF/JPY", "CAD/JPY", "GBP/CAD",
    "USD/BRL", "USD/ARS", "USD/TRY", "USD/MXN", "USD/ZAR",
    "USD/INR", "USD/IDR", "USD/EGP", "USD/NGN", "USD/DZD"
]

bot_active = False  # controle do bot
signals = []        # armazenamento dos sinais gerados

# -----------------------------
# Função para buscar dados na TwelveData
# -----------------------------
async def get_data(symbol: str):
    url = f"https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": "1min",
        "apikey": TWELVEDATA_API_KEY,
        "outputsize": 5
    }
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, params=params)
        data = r.json()
        if "values" not in data:
            raise HTTPException(status_code=400, detail=f"Falha ao consultar TwelveData para {symbol}")
        return data["values"]

# -----------------------------
# Análise simplificada de sinal
# -----------------------------
def analyze_signal(values):
    try:
        latest = float(values[0]["close"])
        previous = float(values[1]["close"])
        variation = ((latest - previous) / previous) * 100

        direction = "CALL" if variation > 0 else "PUT"
        confidence = min(99.9, abs(variation * 100))
        return {"direction": direction, "confidence": confidence}
    except Exception:
        return {"direction": "INDEFINIDO", "confidence": 0}

# -----------------------------
# Geração automática de sinais
# -----------------------------
async def generate_signals():
    global signals
    while True:
        if bot_active:
            print("🤖 Bot ativo — gerando novos sinais...")
            for asset in ASSETS:
                try:
                    data = await get_data(asset)
                    result = analyze_signal(data)
                    if result["confidence"] >= 90:
                        signal = {
                            "asset": asset,
                            "direction": result["direction"],
                            "confidence": result["confidence"],
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        signals.append(signal)
                        print(f"✅ Sinal forte: {asset} → {result['direction']} ({result['confidence']:.2f}%)")
                except Exception as e:
                    print(f"❌ Falha ao processar {asset}: {e}")
        else:
            print("⏸️ Bot desativado — aguardando ativação.")

        await asyncio.sleep(300)  # 5 minutos

# -----------------------------
# Rotas da API
# -----------------------------
@app.get("/")
def root():
    return {"status": "ok", "bot_active": bot_active, "sinais_armazenados": len(signals)}

@app.post("/toggle-bot")
def toggle_bot():
    global bot_active
    bot_active = not bot_active
    return {"bot_active": bot_active}

@app.get("/status-bot")
def status_bot():
    return {"bot_active": bot_active}

@app.get("/signal/live")
def live_signals():
    if not signals:
        return {"detail": "Nenhum sinal disponível ainda"}
    return {"latest_signals": signals[-10:]}

# -----------------------------
# Inicialização automática
# -----------------------------
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(generate_signals())
    print("🚀 Servidor Imperial IA iniciado — monitorando ativos da TwelveData...")
