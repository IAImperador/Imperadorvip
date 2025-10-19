import os
import json
import threading
import time
import websocket
import rel
from fastapi import FastAPI
import uvicorn
from sqlalchemy import create_engine

# ----------------------------------------------------
# 1️⃣ CONEXÃO COM O BANCO DE DADOS (Railway Postgres)
# ----------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            print("✅ Banco de dados conectado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco de dados: {e}")
else:
    print("⚠️ Nenhum banco de dados configurado. Verifique o .env no Railway ou GitHub.")

# ----------------------------------------------------
# 2️⃣ CONFIGURAÇÃO DO APP
# ----------------------------------------------------
app = FastAPI(title="ImperadorVIP - Global Signal Engine")

# Dados de sessão e preços
latest_prices = {}
AUTO_MODE = False
connected = False

# ----------------------------------------------------
# 3️⃣ FUNÇÕES DO WEBSOCKET (QUOTEX)
# ----------------------------------------------------
def on_message(ws, message):
    global latest_prices
    try:
        data = json.loads(message)
        if "price" in data:
            asset = data.get("asset", "unknown")
            price = data.get("price")
            latest_prices[asset] = price
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
    """Inicia conexão com o servidor de dados (Quotex/Deriv/IQ Option futuramente)"""
    try:
        ws_url = "wss://ws.quotex.io/socket.io/"
        ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open,
        )
        ws.run_forever(dispatcher=rel)
        rel.signal(2, rel.abort)
        rel.dispatch()
    except Exception as e:
        print(f"[Erro connect_websocket] {e}")

# ----------------------------------------------------
# 4️⃣ THREAD SECUNDÁRIA (para WebSocket)
# ----------------------------------------------------
@app.on_event("startup")
async def startup_event():
    print("🚀 Iniciando WebSocket em segundo plano...")
    thread = threading.Thread(target=connect_websocket, daemon=True)
    thread.start()

# ----------------------------------------------------
# 5️⃣ ROTAS DA API
# ----------------------------------------------------
@app.get("/")
def root():
    return {
        "app": "ImperadorVIP - Global Signal Engine",
        "auto_mode": AUTO_MODE,
        "feeds": {
            "quotex_connected": connected,
        },
        "symbols_tracked": list(latest_prices.keys())
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/status")
def status():
    return {
        "connected": connected,
        "auto_mode": AUTO_MODE,
        "tracked_assets": list(latest_prices.keys())
    }

@app.get("/price/{asset}")
def price(asset: str):
    price = latest_prices.get(asset.upper())
    if price:
        return {"asset": asset.upper(), "price": price}
    else:
        return {"error": f"Nenhum dado recente para {asset.upper()}"}

@app.post("/mode/{state}")
def set_mode(state: str):
    global AUTO_MODE
    AUTO_MODE = (state.lower() == "auto")
    return {"mode": "auto" if AUTO_MODE else "manual"}

# ----------------------------------------------------
# 6️⃣ EXECUÇÃO LOCAL (para testes)
# ----------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
