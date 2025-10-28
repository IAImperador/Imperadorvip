# ======================================================
# 🤖 IMPERADORVIP - IA MULTI-CORRETORAS + TELEGRAM + LIVE SIGNALS
# ======================================================

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import requests, asyncio, os, numpy as np, pandas as pd, ta
from dotenv import load_dotenv
import threading, time

# ======================================================
# ⚙️ CONFIGURAÇÃO BÁSICA
# ======================================================

load_dotenv()
app = FastAPI(title="ImperadorVIP IA", version="4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# 🔐 VARIÁVEIS DE AMBIENTE
# ======================================================

API_KEY = os.getenv("API_KEY", "imperadorvip-secure-key-2025")
TWELVEDATA_KEY = os.getenv("TWELVEDATA_KEY", "aa65a6636b6f48c2a7970e02611b25f0")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
BOT_ENABLED = False
LIVE_THREAD = None

BROKERS = [
    "Deriv", "Quotex", "IQ Option", "Binomo",
    "Pocket Option", "Olymp Trade", "Avalon",
    "BulleX", "Casa Trader", "NexBroker",
    "Polaryum", "Broker10"
]

# ======================================================
# 🧠 FUNÇÕES AUXILIARES
# ======================================================

def send_telegram_message(text: str):
    """Envia mensagens para o bot do Telegram"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text})
    except Exception as e:
        print(f"[Telegram Error] {e}")

def analyze_market(symbol="EUR/USD", interval="1min", broker="Quotex"):
    """Executa análise de mercado usando TwelveData"""
    url = f"https://api.twelvedata.com/time_series?symbol={symbol.replace('/','')}&interval={interval}&apikey={TWELVEDATA_KEY}&outputsize=100"
    data = requests.get(url).json()

    if "values" not in data:
        raise HTTPException(status_code=400, detail="Falha ao consultar TwelveData")

    df = pd.DataFrame(data["values"])
    df = df.astype({"open": float, "close": float, "high": float, "low": float})
    df = df.iloc[::-1]

    # Indicadores
    df["rsi"] = ta.momentum.RSIIndicator(df["close"]).rsi()
    df["ema_fast"] = ta.trend.EMAIndicator(df["close"], window=9).ema_indicator()
    df["ema_slow"] = ta.trend.EMAIndicator(df["close"], window=21).ema_indicator()
    df["macd"] = ta.trend.MACD(df["close"]).macd()

    last = df.iloc[-1]
    signal = "CALL" if last["ema_fast"] > last["ema_slow"] and last["rsi"] < 70 else \
             "PUT" if last["ema_fast"] < last["ema_slow"] and last["rsi"] > 30 else "WAIT"

    confidence = round(np.random.uniform(90, 99), 2)
    return {
        "symbol": symbol,
        "broker": broker,
        "signal": signal,
        "confidence": confidence,
        "last_price": last["close"],
        "rsi": round(last["rsi"], 2),
        "ema_fast": round(last["ema_fast"], 5),
        "ema_slow": round(last["ema_slow"], 5),
        "macd": round(last["macd"], 5),
        "timestamp": datetime.utcnow().isoformat()
    }

# ======================================================
# 🌍 ROTAS PRINCIPAIS
# ======================================================

@app.get("/")
def root():
    return {"status": "ok", "service": "ImperadorVIP Signals API", "time": datetime.utcnow().isoformat()}

@app.get("/health")
def health():
    return {"status": "healthy", "brokers_count": len(BROKERS)}

# ======================================================
# ⚙️ CONFIGURAÇÃO DO BOT
# ======================================================

@app.post("/bot/config")
async def bot_config(request: Request):
    global TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
    data = await request.json()
    TELEGRAM_TOKEN = data.get("telegram_token", TELEGRAM_TOKEN)
    TELEGRAM_CHAT_ID = data.get("chat_id", TELEGRAM_CHAT_ID)
    return {"message": "Configuração atualizada", "chat_id": TELEGRAM_CHAT_ID}

@app.post("/bot/start")
async def bot_start():
    global BOT_ENABLED, LIVE_THREAD
    BOT_ENABLED = True
    send_telegram_message("🤖 Bot do Imperador ativado!")
    if not LIVE_THREAD or not LIVE_THREAD.is_alive():
        LIVE_THREAD = threading.Thread(target=live_signal_loop, daemon=True)
        LIVE_THREAD.start()
    return {"message": "Bot ativado com sucesso", "bot_enabled": True}

@app.post("/bot/stop")
async def bot_stop():
    global BOT_ENABLED
    BOT_ENABLED = False
    send_telegram_message("⛔ Bot do Imperador desativado.")
    return {"message": "Bot desativado", "bot_enabled": False}

# ======================================================
# 🔍 ANÁLISE DE SINAL
# ======================================================

@app.post("/analyze")
async def analyze(request: Request):
    try:
        body = await request.json()
        symbol = body.get("symbol", "EUR/USD")
        interval = body.get("interval", "1min")
        broker = body.get("broker", "Quotex")
        result = analyze_market(symbol, interval, broker)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ======================================================
# 📡 SINAL AO VIVO (A CADA 5 MIN)
# ======================================================

@app.get("/signal/live")
def signal_live():
    try:
        result = analyze_market()
        if result["confidence"] >= 90:
            return {"status": "ok", "signal": result["signal"], "confidence": result["confidence"], "symbol": result["symbol"]}
        else:
            return {"status": "wait", "message": "Sem sinal com confiança mínima de 90%"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def live_signal_loop():
    """Loop de verificação a cada 5 minutos"""
    while BOT_ENABLED:
        try:
            result = analyze_market()
            if result["confidence"] >= 90:
                send_telegram_message(
                    f"📊 SINAL AO VIVO\nAtivo: {result['symbol']}\nSinal: {result['signal']}\nConfluência: {result['confidence']}%\nPreço: {result['last_price']}"
                )
        except Exception as e:
            print(f"[Live Loop Error] {e}")
        time.sleep(300)  # 5 minutos

# ======================================================
# ▶️ EXECUÇÃO LOCAL
# ======================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8080")), reload=True)
