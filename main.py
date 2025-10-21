# ======================================================
# 🚀 IMPERADORVIP - IA Multi-Corretoras (CORS FIXED)
# ======================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import asyncio

# ======================================================
# ⚙️ CONFIGURAÇÃO DO SERVIDOR E CORS
# ======================================================

app = FastAPI(title="ImperadorVIP IA", version="3.2")

# 🔥 Configuração CORS completa para Base44 e Railway
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://imperadorvip.base44.app",
        "https://app.base44.io",
        "https://studio.base44.io",
        "https://base44.app",
        "https://imperadorvip-production-e55d.up.railway.app",
        "https://imperadorvip-production.up.railway.app",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# 🔧 VARIÁVEIS DE AMBIENTE
# ======================================================

APP_NAME = os.getenv("APP_NAME", "ImperadorVIP")
PORT = int(os.getenv("PORT", "8080"))
DATABASE_URL = os.getenv("DATABASE_URL", "not_configured")
REGION = os.getenv("REGION", "us-east")
TIMEZONE = os.getenv("TIMEZONE", "America/Sao_Paulo")

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
    "Polarium": os.getenv("ENABLE_POLARIUM", "True").lower() == "true",
    "Broker10": os.getenv("ENABLE_CORRETOR10", "True").lower() == "true",
}

BROKERS_ENABLED = [k for k, v in BROKERS.items() if v]

# ======================================================
# 🧠

