from fastapi import FastAPI
from sqlalchemy import create_engine, Column, String, Float, DateTime, Boolean, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import json
import threading
import time
import websocket
import rel
from datetime import datetime

# -------------------------------------------------------
# CONFIGURAÇÕES GERAIS
# -------------------------------------------------------
app = FastAPI(title="ImperadorVIP - Global Signal Engine")

# URL do banco de dados do Railway (adicione nas variáveis de ambiente)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://usuario:senha@host:porta/railway")

# Conexão com o banco
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# -------------------------------------------------------
# TABELAS DO BANCO
# -------------------------------------------------------
class Ativo(Base):
    __tablename__ = "ativos"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True)
    preco = Column(Float)
    fonte = Column(String)  # Quotex, IQ, Deriv, etc.
    atualizado_em = Column(DateTime, default=datetime.utcnow)


# Criar as tabelas
Base.metadata.create_all(bind=engine)

# -------------------------------------------------------
# VARIÁVEIS GLOBAIS
# -------------------------------------------------------
latest_prices = {}
connected = False

# -------------------------------------------------------
# FUNÇÕES DE SUPORTE
# -------------------------------------------------------
def salvar_ativo(asset, price, source="quotex"):
    """Salva ou atualiza o ativo no banco."""
    db = SessionLocal()
    ativo = db.query(Ativo).filter(Ativo.nome == asset).first()
    if ativo:
        ativo.preco = price
        ativo.atualizado_em = datetime.utcnow()
    else:
        ativo = Ativo(nome=asset, preco=price, fonte=source)
        db.add(ativo)
    db.commit()
    db.close()


def on_message(ws, message):
    global latest_prices
    try:
        data = json.loads(message)
        if "price" in data:
            asset = data.get("asset", "unknown")
            price = data.get("price")
            latest_prices[asset] = price
            salvar_ativo(asset, price)
            print(f"[✓] {asset}: {price}")
    except Exception as e:
        print(f"[Erro on_message] {e}")


def on_error(ws, error):
    print(f"[WebSocket Error] {error}")


def on_close(ws, close_status_code, close_msg):
    global connected
    connected = False
    print("[⚠] WebSocket desconectado, tentando reconectar em 5s...")
    time.sleep(5)
    connect_websocket()


def on_open(ws):
    global connected
    connected = True
    print("[🚀] WebSocket conectado com sucesso!")


def connect_websocket():
    try:
        ws_url = "wss://ws.quotex.io/socket.io/"
        ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open,
        )
        ws.run_forever(dispatcher=rel, reconnect=5)
        rel.signal(2, rel.abort)
        rel.dispatch()
    except Exception as e:
        print(f"[Erro connect_websocket] {e}")


# -------------------------------------------------------
# THREAD DE EXECUÇÃO
# -------------------------------------------------------
threading.Thread(target=connect_websocket, daemon=True).start()

# -------------------------------------------------------
# ROTAS FASTAPI
# -------------------------------------------------------
@app.get("/")
def root():
    return {"status": "Servidor IA Imperador ativo", "corretoras": ["Quotex", "IQ Option", "Deriv"]}


@app.get("/ativos")
def listar_ativos():
    db = SessionLocal()
    ativos = db.query(Ativo).all()
    db.close()
    return [{"nome": a.nome, "preco": a.preco, "fonte": a.fonte, "atualizado_em": a.atualizado_em} for a in ativos]


@app.get("/price/{asset}")
def get_price(asset: str):
    db = SessionLocal()
    ativo = db.query(Ativo).filter(Ativo.nome == asset.upper()).first()
    db.close()
    if ativo:
        return {"asset": ativo.nome, "price": ativo.preco, "fonte": ativo.fonte}
    return {"error": "Ativo não encontrado"}


@app.get("/health")
def health():
    return {"status": "ok", "connected": connected}

# -------------------------------------------------------
# EXECUÇÃO LOCAL (opcional)
# -------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
