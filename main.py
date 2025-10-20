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

app = FastAPI(title="ImperadorVIP IA", version="2.0")

# 🔥 Permite conexões da Base44 e outros domínios
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # ou substitua por: "https://imperadorvip.base44.app", "https://app.base44.io"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# 🔧 VARIÁVEIS DE AMBIENTE
# ======================================================

APP_NAME = os.getenv("APP_NAME", "ImperadorVIP")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
PORT = int(os.getenv("PORT", "8080"))
DATABASE_URL = os.getenv("DATABASE_URL", "not_configured")
REGION = os.getenv("REGION", "us-east")
TIMEZONE = os.getenv("TIMEZONE", "America/Sao_Paulo")
API_KEY = os.getenv("API_KEY", "imperadorvip-secure-key-2025")

# ======================================================
# 💹 CORRETORAS SUPORTADAS
# ======================================================

BROKERS = {
    "Deriv": os.getenv("ENABLE_DERIV", "False").lower() == "true",
    "Quotex": os.getenv("ENABLE_QUOTEX", "False").lower() == "true",
    "IQ Option": os.getenv("ENABLE_IQOPTION", "False").lower() == "true",
    "Binomo": os.getenv("ENABLE_BINOMO", "False").lower() == "true",
    "Pocket Option": os.getenv("ENABLE_POCKETOPTION", "False").lower() == "true",
    "Olymp Trade": os.getenv("ENABLE_OLYMPTRADE", "False").lower() == "true",
    "Avalon": os.getenv("ENABLE_AVALON", "False").lower() == "true",
    "BulleX": os.getenv("ENABLE_BULLEX", "False").lower() == "true",
    "Casa Trader": os.getenv("ENABLE_CASATRADER", "False").lower() == "true",
    "NexBroker": os.getenv("ENABLE_NEXBROKER", "False").lower() == "true",
    "Polarium": os.getenv("ENABLE_POLARIUM", "False").lower() == "true",
    "Broker10": os.getenv("ENABLE_CORRETOR10", "False").lower() == "true",
}

BROKERS_ENABLED = [k for k, v in BROKERS.items() if v]

# ======================================================
# 🧠 INICIALIZAÇÃO DA IA
# ======================================================

async def initialize_ai():
    print("===============================================")
    print(f"🔥 Inicializando IA {APP_NAME}...")
    print(f"🌍 Região: {REGION} | Fuso horário: {TIMEZONE}")
    print(f"🧩 Corretoras Ativas: {BROKERS_ENABLED}")
    print(f"📦 Banco: {DATABASE_URL}")
    print("===============================================")
    await asyncio.sleep(1)
    print("✅ IA carregada e pronta!")

# ======================================================
# 🌐 ROTAS PRINCIPAIS
# ======================================================

@app.get("/")
async def root():
    return {
        "status": "online",
        "app": APP_NAME,
        "brokers_enabled": BROKERS_ENABLED,
        "message": f"IA {APP_NAME} conectada com sucesso.",
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "region": REGION,
        "timezone": TIMEZONE,
        "brokers_count": len(BROKERS_ENABLED),
    }


@app.get("/brokers")
async def list_brokers():
    return {
        "enabled": BROKERS_ENABLED,
        "all_supported": list(BROKERS.keys()),
    }

# ======================================================
# 🚀 EVENTOS AUTOMÁTICOS
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

