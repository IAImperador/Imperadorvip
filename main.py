from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# 🔥 ADICIONE ISTO - CONFIGURAÇÃO CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todas as origens
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos os métodos
    allow_headers=["*"],  # Permite todos os headers
)

# 🚀 IMPERADORVIP - Servidor IA para Análise de Corretores
# ======================================================

from fastapi import FastAPI
import os
import asyncio

# ======================================================
# ⚙️ CONFIGURAÇÕES INICIAIS
# ======================================================

app = FastAPI(title="ImperadorVIP IA", version="1.0.0")

# Carrega variáveis de ambiente
APP_NAME = os.getenv("APP_NAME", "ImperadorVIP")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
PORT = int(os.getenv("PORT", "8080"))
DATABASE_URL = os.getenv("DATABASE_URL", "")
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
    "CasaTrader": os.getenv("ENABLE_CASATRADER", "False").lower() == "true",
    "NexBroker": os.getenv("ENABLE_NEXBROKER", "False").lower() == "true",
    "Polarium": os.getenv("ENABLE_POLARIUM", "False").lower() == "true",
    "Corretor10": os.getenv("ENABLE_CORRETOR10", "False").lower() == "true",
}

BROKERS_ENABLED = [k for k, v in BROKERS.items() if v]

# ======================================================
# 🧠 INICIALIZAÇÃO DA IA
# ======================================================

async def initialize_ai():
    print("===============================================")
    print(f"🔥 IA {APP_NAME} iniciando...")
    print(f"🌍 Região: {REGION} | Fuso horário: {TIMEZONE}")
    print(f"📡 Banco de Dados: {DATABASE_URL}")
    print(f"🤖 Corretoras Ativas: {BROKERS_ENABLED}")
    print("===============================================")
    await asyncio.sleep(1)
    print("✅ IA carregada com sucesso!")

# ======================================================
# 🌐 ROTAS PRINCIPAIS
# ======================================================

@app.get("/")
async def root():
    return {
        "status": "online",
        "app": APP_NAME,
        "brokers_enabled": BROKERS_ENABLED,
        "message": f"IA {APP_NAME} ativo e rodando com sucesso."
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "brokers_count": len(BROKERS_ENABLED)}

@app.get("/brokers")
async def list_brokers():
    return {
        "enabled": BROKERS_ENABLED,
        "all": list(BROKERS.keys())
    }

# ======================================================
# 🧩 EXECUÇÃO LOCAL
# ======================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT)


