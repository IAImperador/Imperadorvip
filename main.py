from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
import asyncio
import uvicorn

# Carregar variáveis do .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
APP_NAME = os.getenv("APP_NAME", "ImperadorVIP")

app = FastAPI(title=f"{APP_NAME} - Mecanismo de Sinal Global")

# Conexão assíncrona com o banco de dados PostgreSQL
engine = create_async_engine(DATABASE_URL, echo=True, future=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

@app.on_event("startup")
async def startup_event():
    print("🚀 Servidor iniciado com sucesso!")
    print("📡 Conectando ao banco de dados...")
    async with engine.begin() as conn:
        await conn.run_sync(lambda conn: None)
    print("✅ Banco conectado com sucesso!")

@app.get("/")
async def root():
    return {
        "app": APP_NAME,
        "status": "online",
        "feeds": {
            "deriv_connected": True,
            "quotex_connected": False,
            "iq_connected": False
        },
        "symbols_tracked": [
            "CRASH500", "BOOM500", "BOOM1000", "CRASH1000",
            "CRASH600", "BOOM300", "CRASH300", "BOOM900"
        ]
    }

@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 Encerrando servidor...")
    await engine.dispose()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
