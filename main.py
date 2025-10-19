import os
import json
import asyncio
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
import websockets

# === CONFIGURAÇÃO INICIAL === #
load_dotenv()
app = FastAPI(title="ImperadorVIP - Global Signal Engine")

# === CONFIGURAÇÃO DO BANCO DE DADOS === #
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DATABASE_PUBLIC_URL")
if not DATABASE_URL:
    raise ValueError("❌ Variável DATABASE_URL não encontrada no Railway. Configure-a em Variables.")

# Corrige prefixo para compatibilidade com SQLAlchemy
DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# === MODELO DE TABELA === #
class Signal(Base):
    __tablename__ = "signals"
    id = Column(Integer, primary_key=True, index=True)
    asset = Column(String, nullable=False)
    strength = Column(Float)
    direction = Column(String)
    platform = Column(String)
    timestamp = Column(String)
    active = Column(Boolean, default=True)

# Cria tabela automaticamente
Base.metadata.create_all(bind=engine)

# === STATUS DO SISTEMA === #
STATUS = {
    "feeds": {
        "deriv_connected": False,
        "quotex_connected": False,
        "iq_connected": False
    },
    "symbols_tracked": [],
    "signals_count": 0
}

# === CONEXÕES SIMULADAS === #
async def connect_deriv():
    STATUS["feeds"]["deriv_connected"] = True
    STATUS["symbols_tracked"] = [
        "CRASH1000", "BOOM1000", "BOOM500", "CRASH500",
        "CRASH300N", "BOOM300N", "RDBEAR", "RDBULL",
        "cryBTCUSD", "cryETHUSD", "BOOM900", "CRASH900",
        "BOOM600", "CRASH600"
    ]
    print("[DERIV] ✅ Conectado e recebendo dados...")
    while True:
        await asyncio.sleep(30)
        with SessionLocal() as db:
            db.add(Signal(asset="BOOM1000", strength=85.5, direction="CALL", platform="Deriv", timestamp="auto"))
            db.commit()
        STATUS["signals_count"] += 1

async def connect_quotex():
    STATUS["feeds"]["quotex_connected"] = True
    print("[QUOTEX] ✅ Conectado (simulado).")

async def connect_iq():
    STATUS["feeds"]["iq_connected"] = True
    print("[IQ OPTION] ✅ Conectado (simulado).")

# === ROTAS === #
@app.get("/")
def root():
    return JSONResponse({
        "app": "ImperadorVIP - Global Signal Engine (Public Feeds)",
        "feeds": STATUS["feeds"],
        "symbols_tracked": STATUS["symbols_tracked"],
        "signals_count": STATUS["signals_count"]
    })

@app.get("/sessions")
def get_sessions():
    return JSONResponse(STATUS)

@app.post("/connect/{platform}")
async def connect_platform(platform: str):
    if platform.lower() == "deriv":
        asyncio.create_task(connect_deriv())
    elif platform.lower() == "quotex":
        asyncio.create_task(connect_quotex())
    elif platform.lower() == "iq":
        asyncio.create_task(connect_iq())
    else:
        return JSONResponse({"error": "Plataforma desconhecida"}, status_code=400)
    return JSONResponse({"message": f"{platform.upper()} conectado com sucesso."})

# === INICIALIZAÇÃO AUTOMÁTICA === #
@app.on_event("startup")
async def startup_event():
    print("🚀 Iniciando feeds automáticos...")
    asyncio.create_task(connect_deriv())
    asyncio.create_task(connect_quotex())
    asyncio.create_task(connect_iq())

# === EXECUÇÃO LOCAL === #
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
