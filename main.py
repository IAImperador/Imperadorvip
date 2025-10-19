import os
from fastapi import FastAPI
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

# === Carregar variáveis de ambiente ===
load_dotenv()

# === Configurações do banco de dados ===
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL não encontrado. Verifique seu arquivo .env")

engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# === Inicializar app FastAPI ===
app = FastAPI(
    title="ImperadorVIP - Mecanismo de Sinal Global",
    description="Feeds Públicos e Módulo de Estratégia",
    version="2.0"
)

# === Inicializar scheduler ===
scheduler = AsyncIOScheduler()

# === Função exemplo de tarefa programada ===
async def verificar_status():
    print("✅ Sistema ativo e verificando conexões...")

scheduler.add_job(verificar_status, "interval", minutes=1)
scheduler.start()


@app.get("/")
async def root():
    return {
        "app": "ImperadorVIP - Mecanismo de Sinal Global (Feeds Públicos)",
        "feeds": {
            "deriv_connected": True,
            "quotex_connected": False,
            "iq_connected": False,
            "symbols_tracked": [
                "CRASH900", "BOOM1000", "CRASH1000", "BOOM600",
                "BOOM300", "CRASH600", "RDBULL", "cryETHUSD",
                "CRASH500", "BOOM900", "cryBTCUSD", "CRASH300N",
                "RDBEAR", "BOOM500"
            ]
        }
    }


# === Inicialização do banco de dados ===
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("🚀 Aplicação iniciada e banco conectado!")


@app.on_event("shutdown")
async def on_shutdown():
    await engine.dispose()
    print("🛑 Aplicação finalizada com segurança.")
