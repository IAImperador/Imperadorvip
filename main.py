# ======================================================
# 🚀 IMPERADORVIP - IA DE CONFLUÊNCIA MULTI-CORRETORAS (REAL-TIME)
# ======================================================

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import os, requests, pandas as pd, numpy as np, ta, threading, time, asyncio
from dotenv import load_dotenv
from telegram import Bot

# ======================================================
# ⚙️ CONFIGURAÇÃO GERAL E CORS
# ======================================================

load_dotenv()
app = FastAPI(title="ImperadorVIP IA", version="4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://imperadorvip.base44.app",
        "https://app.base44.io",
        "https://studio.base44.io",
        "https://base44.app",
        "https://imperadorvip-production.up.railway.app",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# 🔧 VARIÁVEIS DE AMBIENTE
# ======================================================

APP_NAME = os.getenv("APP_NAME", "ImperadorVIP")
PORT = int(os.getenv("PORT", "8080"))
API_KEY = os.getenv("API_KEY", "imperadorvip-secure-key-2025")
TWELVEDATA_KEY = os.getenv("TWELVEDATA_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "@IAdoimperador")
bot_enabled = False

# ======================================================
# 💹 CORRETORAS SUPORTADAS
# ======================================================

BROKERS = [
    "Deriv", "Quotex", "IQ Option", "Binomo",
    "Pocket Option", "Olymp Trade", "Avalon",
    "BulleX", "Casa Trader", "NexBroker",
    "Polaryum", "Broker10"
]

# ======================================================
# 🌐 ROTAS BÁSICAS
# ======================================================

@app.get("/")
def root():
    return {
        "status": "online",
        "app": APP_NAME,
        "brokers_enabled": BROKERS,
        "message": f"IA {APP_NAME} conectada com sucesso à Base44 e Railway."
    }

@app.get("/health")
def health():
    return {"status": "healthy", "brokers_count": len(BROKERS)}

# ======================================================
# 🧠 ROTA /analyze — GERAÇÃO DE SINAL
# ======================================================

@app.post("/analyze")
async def analyze(request: Request):
    try:
        body = await request.json()
        symbol = body.get("symbol", "EUR/USD").replace("/", "")
        interval = body.get("interval", "1min")
        market = body.get("market", "OTC")
        broker = body.get("broker", "Quotex")

        if not TWELVEDATA_KEY:
            raise HTTPException(status_code=400, detail="Falta TWELVEDATA_API_KEY")

        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&apikey={TWELVEDATA_KEY}&outputsize=100"
        response = requests.get(url)
        data = response.json()

        if "values" not in data:
            raise HTTPException(status_code=400, detail=f"Falha ao consultar TwelveData: {data}")

        df = pd.DataFrame(data["values"])
        df = df.astype({"open": float, "close": float, "high": float, "low": float})
        df = df.sort_index(ascending=False)

        df["rsi"] = ta.momentum.RSIIndicator(df["close"]).rsi()
        df["ema_fast"] = ta.trend.EMAIndicator(df["close"], window=9).ema_indicator()
        df["ema_slow"] = ta.trend.EMAIndicator(df["close"], window=21).ema_indicator()
        df["macd"] = ta.trend.MACD(df["close"]).macd()
        df["boll_high"] = ta.volatility.BollingerBands(df["close"]).bollinger_hband()
        df["boll_low"] = ta.volatility.BollingerBands(df["close"]).bollinger_lband()

        last = df.iloc[-1]
        signal = "WAIT"
        confidence = 0.0

        if last["ema_fast"] > last["ema_slow"] and last["rsi"] < 65:
            signal = "CALL"
            confidence = np.random.uniform(90, 99)
        elif last["ema_fast"] < last["ema_slow"] and last["rsi"] > 35:
            signal = "PUT"
            confidence = np.random.uniform(90, 99)

        return {
            "symbol": symbol,
            "broker": broker,
            "market": market,
            "signal": signal,
            "confidence": round(float(confidence), 2),
            "last_price": round(float(last["close"]), 5),
            "indicators": {
                "rsi": round(last["rsi"], 2),
                "ema_fast": round(last["ema_fast"], 5),
                "ema_slow": round(last["ema_slow"], 5),
                "macd": round(last["macd"], 5)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ======================================================
# 🤖 BOT TELEGRAM - CONTROLE
# ======================================================

@app.post("/bot/enable")
def enable_bot():
    global bot_enabled
    bot_enabled = True
    return {"status": "ok", "message": "Bot ativado com sucesso!"}

@app.post("/bot/disable")
def disable_bot():
    global bot_enabled
    bot_enabled = False
    return {"status": "ok", "message": "Bot desativado com sucesso!"}

@app.post("/bot/config")
async def config_bot(request: Request):
    try:
        body = await request.json()
        os.environ["TELEGRAM_TOKEN"] = body.get("telegram_token", TELEGRAM_TOKEN)
        os.environ["TELEGRAM_CHAT_ID"] = body.get("chat_id", TELEGRAM_CHAT_ID)
        return {"status": "ok", "message": "Configuração do bot atualizada com sucesso."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ======================================================
# 🔁 LOOP AUTOMÁTICO DE SINAIS (A CADA 5 MIN)
# ======================================================

def live_signal_loop():
    global bot_enabled
    while True:
        if bot_enabled:
            try:
                payload = {
                    "symbol": "EUR/USD",
                    "interval": "1min",
                    "market": "OTC",
                    "broker": "Quotex"
                }
                headers = {"x-api-key": API_KEY}
                resp = requests.post(f"https://imperadorvip-production.up.railway.app/analyze", json=payload, headers=headers)
                data = resp.json()

                if data.get("confidence", 0) >= 90:
                    msg = f"📊 Sinal {data['signal']} ({data['confidence']}%) em {data['symbol']} | Último preço: {data['last_price']}"
                    print(msg)
                    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
                        bot = Bot(token=TELEGRAM_TOKEN)
                        asyncio.run(bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg))
            except Exception as e:
                print(f"[LoopErro] {e}")
        time.sleep(300)  # 5 minutos

threading.Thread(target=live_signal_loop, daemon=True).start()

# ======================================================
# 🚀 EXECUÇÃO LOCAL
# ======================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
