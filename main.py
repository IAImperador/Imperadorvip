import os
import asyncio
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import httpx
import websockets
import json

# ========================
# CONFIGURAÇÕES INICIAIS
# ========================

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./signals.db")

# Banco de dados SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Configuração de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ImperadorVIP")

# ========================
# INICIALIZAÇÃO DO APP
# ========================

app = FastAPI(title="ImperadorVIP - Mecanismo de Sinal Global (Feeds Públicos)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================
# VARIÁVEIS GLOBAIS
# ========================

connections = {
    "deriv": False,
    "quotex": False,
    "iq": False,
}

symbols_tracked = [
    "CRASH900", "BOOM1000", "CRASH1000", "BOOM600",
    "BOOM300N", "CRASH600", "RDBULL", "cryETHUSD",
    "CRASH500", "BOOM900", "cryBTCUSD", "CRASH300N",
    "RDBEAR", "BOOM500"
]

sessions = {}

# ========================
# ROTAS BÁSICAS
# ========================

@app.get("/")
async def root():
    """Status geral do servidor"""
    return {
        "app": "ImperadorVIP - Mecanismo de Sinal Global (Feeds Públicos)",
        "feeds": {
            "deriv_connected": connections["deriv"],
            "quotex_connected": connections["quotex"],
            "iq_connected": connections["iq"],
        },
        "symbols_tracked": symbols_tracked,
    }

# ========================
# DERIV (Conexão WebSocket)
# ========================

async def connect_deriv():
    """Mantém conexão ativa com Deriv"""
    deriv_url = "wss://ws.derivws.com/websockets/v3?app_id=1089"
    try:
        async with websockets.connect(deriv_url) as ws:
            connections["deriv"] = True
            logger.info("✅ Conectado à Deriv WebSocket")
            while True:
                await ws.send(json.dumps({"ping": 1}))
                await asyncio.sleep(10)
    except Exception as e:
        connections["deriv"] = False
        logger.error(f"❌ Erro na conexão Deriv: {e}")
        await asyncio.sleep(5)
        await connect_deriv()

@app.on_event("startup")
async def startup_event():
    """Inicia conexões automáticas"""
    asyncio.create_task(connect_deriv())

# ========================
# QUOTEX E IQ OPTION
# ========================

@app.post("/connect/quotex")
async def connect_quotex(data: dict):
    """Simula conexão à Quotex"""
    email = data.get("email")
    password = data.get("password")
    user_id = data.get("user_id")

    if not email or not password:
        raise HTTPException(status_code=400, detail="Credenciais inválidas")

    # Aqui poderia ter integração real via API ou Selenium
    connections["quotex"] = True
    sessions[user_id] = {"broker": "Quotex", "email": email}
    logger.info(f"Usuário {email} conectado na Quotex ✅")

    return {"status": "connected", "broker": "quotex", "email": email}


@app.post("/connect/iq")
async def connect_iq(data: dict):
    """Simula conexão à IQ Option"""
    email = data.get("email")
    password = data.get("password")
    user_id = data.get("user_id")

    if not email or not password:
        raise HTTPException(status_code=400, detail="Credenciais inválidas")

    # Aqui poderia ter integração real com API não-oficial IQ Option
    connections["iq"] = True
    sessions[user_id] = {"broker": "IQ Option", "email": email}
    logger.info(f"Usuário {email} conectado na IQ Option ✅")

    return {"status": "connected", "broker": "iqoption", "email": email}

# ========================
# STATUS DAS SESSÕES
# ========================

@app.get("/sessions")
async def list_sessions():
    """Lista usuários conectados"""
    return {
        "total_users": len(sessions),
        "sessions": sessions,
        "brokers_status": connections,
    }

# ========================
# ERROS PERSONALIZADOS
# ========================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Erro global: {exc}")
    return {"error": str(exc)}

# ========================
# EXECUÇÃO LOCAL (DEV)
# ========================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))

