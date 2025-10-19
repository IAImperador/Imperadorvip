import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# ============================================================
# 🔹 Carregar variáveis de ambiente (.env)
# ============================================================
load_dotenv()

# ============================================================
# 🔹 Configuração do Banco de Dados (PostgreSQL assíncrono)
# ============================================================
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:PuypxUfIHIxWXuTuIEIAGoGIFdYeUgpt@mainline.proxy.rlwy.net:16060/railway"
)

# Criar engine assíncrona
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# Criar fábrica de sessões assíncronas
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# Base para os modelos ORM
Base = declarative_base()

# ============================================================
# 🔹 Inicialização do FastAPI
# ============================================================
app = FastAPI(
    title="ImperadorVIP API",
    version="1.0",
    description="🚀 API para integração do sistema ImperadorVIP em tempo real."
)

# Configurar CORS para permitir requisições de apps externos
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 🔹 Dependência de sessão de banco
# ============================================================
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# ============================================================
# 🔹 Rotas principais
# ============================================================
@app.get("/")
async def root():
    return {"status": "✅ API ImperadorVIP Online e Conectada!"}

@app.get("/health")
async def health_check():
    return {"ok": True, "db": str(engine.url)}

# ============================================================
# 🔹 Eventos de inicialização e encerramento
# ============================================================
@app.on_event("startup")
async def startup_event():
    print("🚀 Iniciando sistema e conectando ao banco de dados...")

@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 Encerrando servidor e fechando conexões...")

# ============================================================
# 🔹 Execução local (modo debug)
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)

