from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import requests
import os
import random
from datetime import datetime

app = FastAPI(title="ImperadorVIP Signal Engine")

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Variáveis ---
TWELVEDATA_KEY = os.getenv("TWELVEDATA_API_KEY", "")
API_KEY = os.getenv("API_KEY", "imperadorvip-secure-key-2025")

if not TWELVEDATA_KEY:
    print("⚠️ TWELVEDATA_KEY não definida. Configure no Railway.")

# --- Simulação de Análise ---
def analisar_confluencias():
    """Simula cálculo de confiança e decisão de CALL/PUT"""
    direcao = random.choice(["CALL", "PUT"])
    confianca = random.randint(70, 100)
    return {"sinal": direcao, "confianca": confianca}

# --- Endpoint base de saúde ---
@app.get("/")
def home():
    return {"status": "online", "timestamp": datetime.now().isoformat()}

# --- Endpoint para análise manual ---
@app.post("/analyze")
def analisar_sinal(req: Request):
    try:
        data = requests.get(
            f"https://api.twelvedata.com/time_series?symbol=EUR/USD&interval=1min&apikey={TWELVEDATA_KEY}"
        ).json()
        if "values" not in data:
            raise HTTPException(status_code=400, detail="Falha ao consultar TwelveData")

        resultado = analisar_confluencias()
        return {
            "timestamp": datetime.now().isoformat(),
            "sinal": resultado["sinal"],
            "confianca": resultado["confianca"],
            "base": "EUR/USD",
            "status": "ok",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- ✅ Nova rota /signal/live ---
@app.get("/signal/live")
async def sinal_ao_vivo():
    """Envia sinais de 60 em 60s, apenas com confiança >= 90%"""
    try:
        print("🚀 Modo Live iniciado...")
        resultados = []

        for i in range(3):  # 3 ciclos (3 minutos)
            analise = analisar_confluencias()
            if analise["confianca"] >= 90:
                resultado = {
                    "hora": datetime.now().strftime("%H:%M:%S"),
                    "ativo": "EUR/USD",
                    "sinal": analise["sinal"],
                    "confianca": analise["confianca"],
                    "status": "📡 Enviado",
                }
                print(resultado)
                resultados.append(resultado)
            else:
                print(f"Ignorado ({analise['confianca']}%)")

            await asyncio.sleep(60)

        return {"status": "finalizado", "resultados": resultados}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro em modo live: {str(e)}")

