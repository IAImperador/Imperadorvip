from fastapi import FastAPI
import json
import threading
import time
import websocket
import uvicorn

app = FastAPI(title="ImperadorVIP - Global Signal Engine")

# -------------------------------
# CONFIGURAÇÃO GERAL
# -------------------------------
QUOTEX_WS_URL = "wss://ws.quotex.io/socket.io/"
EMAIL = "seu_email@example.com"
PASSWORD = "sua_senha"

current_prices = {}
current_candles = {}
ws_connection = None
connected = False

# -------------------------------
# FUNÇÕES DE CALLBACK
# -------------------------------
def on_message(ws, message):
    """Processar mensagens recebidas"""
    global current_prices, current_candles
    try:
        data = json.loads(message)
        if "asset" in data and "price" in data:
            asset = data["asset"]
            current_prices[asset] = {
                "price": data["price"],
                "timestamp": time.time()
            }
            print(f"✅ Preço atualizado: {asset} = {data['price']}")

        elif "candle" in data:
            asset = data["candle"]["asset"]
            if asset not in current_candles:
                current_candles[asset] = []
            current_candles[asset].append({
                "open": data["candle"]["open"],
                "high": data["candle"]["high"],
                "low": data["candle"]["low"],
                "close": data["candle"]["close"],
                "volume": data["candle"].get("volume", 0),
                "time": data["candle"]["time"]
            })
            # limitar a 100 candles
            if len(current_candles[asset]) > 100:
                current_candles[asset] = current_candles[asset][-100:]
    except Exception as e:
        print(f"Erro ao processar mensagem: {e}")

def on_error(ws, error):
    print(f"❌ Erro WebSocket: {error}")

def on_close(ws, close_status_code, close_msg):
    global connected
    connected = False
    print(f"⚠️ Conexão fechada: {close_status_code}. Tentando reconectar em 5s...")
    time.sleep(5)
    connect_websocket()

def on_open(ws):
    global connected
    connected = True
    print("✅ Conectado ao WebSocket da Quotex!")
    
    # autenticação
    auth_message = {
        "type": "auth",
        "email": EMAIL,
        "password": PASSWORD
    }
    ws.send(json.dumps(auth_message))
    
    # inscrição nos pares desejados
    assets = ["EURUSD", "GBPUSD", "USDJPY", "BTCUSD"]
    for asset in assets:
        subscribe_message = {
            "type": "subscribe",
            "asset": asset,
            "period": 60
        }
        ws.send(json.dumps(subscribe_message))
        print(f"📊 Assinado: {asset}")

# -------------------------------
# CONEXÃO WEBSOCKET
# -------------------------------
def connect_websocket():
    global ws_connection
    try:
        ws_connection = websocket.WebSocketApp(
            QUOTEX_WS_URL,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        # Removemos completamente o `rel` — agora é estável no Railway
        ws_connection.run_forever(reconnect=5)
    except Exception as e:
        print(f"Erro ao conectar WebSocket: {e}")

# -------------------------------
# INICIALIZAÇÃO EM THREAD
# -------------------------------
@app.on_event("startup")
async def startup():
    thread = threading.Thread(target=connect_websocket, daemon=True)
    thread.start()
    print("🚀 WebSocket iniciado em background")

# -------------------------------
# ROTAS FASTAPI
# -------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/status")
def get_status():
    return {
        "connected": connected,
        "assets_tracking": list(current_prices.keys()),
        "total_candles": sum(len(v) for v in current_candles.values())
    }

@app.get("/price/{asset}")
def get_price(asset: str):
    asset = asset.upper()
    if asset in current_prices:
        return current_prices[asset]
    return {"error": "Asset not found"}

@app.get("/candles/{asset}")
def get_candles(asset: str):
    asset = asset.upper()
    if asset in current_candles:
        return {"candles": current_candles[asset]}
    return {"error": "Asset not found"}

# -------------------------------
# EXECUÇÃO LOCAL
# -------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
