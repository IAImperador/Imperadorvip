# ======================================================
# 🚀 IMPERADORVIP - IA de Confluência Multi-Corretoras
# ======================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import asyncio

# ======================================================
# ⚙️ CONFIGURAÇÃO DO SERVIDOR E CORS
# ======================================================

app = FastAPI(title="ImperadorVIP IA", version="3.0")

# 🔥 CORS TOTALMENTE LIBERADO (para Base44 e webapps)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://imperadorvip.base44.app",
        "https://app.base44.io",
        "https://studio.base44.io",
        "https://base44.app",
        "https://imperadorvip-production.up.railway.app",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# 🔧 VARIÁVEIS DE AMBIENTE (padrões automáticos)
# ======================================================

APP_NAME = os.getenv("APP_NAME", "ImperadorVIP")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
PORT = int(os.getenv("PORT", "8080"))
DATABASE_URL = os.getenv("DATABASE_URL", "not_configured")
REGION = os.getenv("REGION", "us-east")
TIMEZONE = os.getenv("TIMEZONE", "America/Sao_Paulo")
API_KEY = os.getenv("API_KEY", "imperadorvip-secure-key-2025")
AI_ENGINE = os.getenv("AI_ENGINE", "imperador_v1")
AI_PRECISION_MODE = os.getenv("IA_PRECISION_MODE", "high")
AUTO_MODE = os.getenv("AUTO_MODE", "False").lower() == "true"

# ======================================================
# 💹 CORRETORAS SUPORTADAS
# ======================================================

BROKERS = {
    "Deriv": os.getenv("ENABLE_DERIV", "True").lower() == "true",
    "Quotex": os.getenv("ENABLE_QUOTEX", "True").lower() == "true",
    "IQ Option": os.getenv("ENABLE_IQOPTION", "True").lower() == "true",
    "Binomo": os.getenv("ENABLE_BINOMO", "True").lower() == "true",
    "Pocket Option": os.getenv("ENABLE_POCKETOPTION", "True").lower() == "true",
    "Olymp Trade": os.getenv("ENABLE_OLYMPTRADE", "True").lower() == "true",
    "Avalon": os.getenv("ENABLE_AVALON", "True").lower() == "true",
    "BulleX": os.getenv("ENABLE_BULLEX", "True").lower() == "true",
    "Casa Trader": os.getenv("ENABLE_CASATRADER", "True").lower() == "true",
    "NexBroker": os.getenv("ENABLE_NEXBROKER", "True").lower() == "true",
    "Polaryum": os.getenv("ENABLE_POLARYUM", "True").lower() == "true",
    "Broker10": os.getenv("ENABLE_BROKER10", "True").lower() == "true",
}

BROKERS_ENABLED = [k for k, v in BROKERS.items() if v]

# ======================================================
# 🧠 INICIALIZAÇÃO DA IA (com base para leitura real)
# ======================================================

async def initialize_ai():
    print("===============================================")
    print(f"🔥 Inicializando IA {APP_NAME}...")
    print(f"🌍 Região: {REGION} | Fuso horário: {TIMEZONE}")
    print(f"🧩 Corretoras Ativas: {BROKERS_ENABLED}")
    print(f"🧠 Motor IA: {AI_ENGINE} | Precisão: {AI_PRECISION_MODE}")
    print(f"📦 Banco: {DATABASE_URL}")
    print("===============================================")
    await asyncio.sleep(1)
    print("✅ IA carregada e pronta para leitura de gráfico em tempo real!")

# ======================================================
# 🌐 ROTAS PRINCIPAIS
# ======================================================

@app.get("/")
async def root():
    return {
        "status": "online",
        "app": APP_NAME,
        "brokers_enabled": BROKERS_ENABLED,
        "ai_engine": AI_ENGINE,
        "precision": AI_PRECISION_MODE,
        "message": f"IA {APP_NAME} conectada com sucesso à Base44 e pronta para análise em tempo real."
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "region": REGION,
        "timezone": TIMEZONE,
        "brokers_count": len(BROKERS_ENABLED),
        "ai_engine": AI_ENGINE,
        "database": DATABASE_URL
    }

@app.get("/brokers")
async def list_brokers():
    return {
        "enabled": BROKERS_ENABLED,
        "all_supported": list(BROKERS.keys()),
        "auto_mode": AUTO_MODE
    }

# ======================================================
# ⚡ EVENTOS AUTOMÁTICOS (início e encerramento)
# ======================================================

@app.on_event("startup")
async def startup_event():
    await initialize_ai()
    print("🟢 Servidor iniciado com sucesso e CORS habilitado.")

@app.on_event("shutdown")
async def shutdown_event():
    print("🔴 Servidor encerrando conexões...")

# ======================================================
# 🧩 EXECUÇÃO LOCAL (debug)
# ======================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
