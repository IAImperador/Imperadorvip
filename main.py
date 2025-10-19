import os
import asyncio
from fastapi import FastAPI
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ==========================
# 🔧 Configuração do Banco
# ==========================

# Tenta pegar o DATABASE_URL do Railway
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DATABASE_PUBLIC_URL")

if not DATABASE_URL:
    raise ValueError("❌ Nenhuma variável DATABASE_URL ou DATABASE_PUBLIC_URL encontrada no ambiente Railway.")

# Corrige URL caso venha com 'postgres://' (precisa ser 'postgresql://')
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")

# Cria engine SQLAlchemy
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================
# 🧱 Modelos
# ==========================
class Ativo(Base):
    __tablename__ = "ativos"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, nullable=False)
    preco = Column(Float, nullable=True)

# Cria as tabelas automaticamente
Base.metadata.create_all(bind=engine)

# ==========================
# 🚀 App Principal
# ==========================
app = FastAPI(title="ImperadorVIP - Global Signal Engine")

@app.get("/")
async def root():
    """Status do sistema"""
    return {
        "app": "ImperadorVIP - Global Signal Engine (Public Feeds)",
        "feeds": {
            "deriv_connected": True,
            "quotex_connected": False,
            "iq_connected": False
        },
        "database": "✅ Conectado com sucesso ao PostgreSQL"
    }

@app.get("/ativos")
async def listar_ativos():
    """Lista todos os ativos registrados no banco"""
    db = SessionLocal()
    ativos = db.query(Ativo).all()
    db.close()
    return [{"id": a.id, "nome": a.nome, "preco": a.preco} for a in ativos]

@app.post("/ativos")
async def adicionar_ativo(nome: str, preco: float = None):
    """Adiciona novo ativo"""
    db = SessionLocal()
    novo = Ativo(nome=nome, preco=preco)
    db.add(novo)
    db.commit()
    db.refresh(novo)
    db.close()
    return {"✅ Novo ativo adicionado": {"id": novo.id, "nome": novo.nome, "preco": novo.preco}}

# ==========================
# 🔁 Inicialização
# ==========================
if __name__ == "__main__":
    import uvicorn
    print("🚀 Servidor iniciado em http://0.0.0.0:8080")
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
