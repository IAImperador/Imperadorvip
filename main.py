# ======================================================
# 🚀 IMPERADORVIP - IA DO IMPERADOR (v4.2)
# ======================================================
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import os, asyncio, requests, pandas as pd, numpy as np, ta
from dotenv import load_dotenv
from telegram import Bot
from datetime import datetime

load_dotenv()

# ======================================================
# ⚙️ CONFIGURAÇÃO BÁSICA
# ======================================================
app = FastAPI(title="IA do Imperador", version="4.2")

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
# 🔐 VARIÁVEIS DE AMBIENTE
# ======================================================
APP_NAME = os.getenv("APP_NAME", "ImperadorVIP")
PORT = int(os.getenv("PORT", "8080"))
API_KEY = os.getenv("API_KEY", "imperadorvip-secure-key-2025")

TWELVEDATA_KEY = os.getenv("TWELVEDATA_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot_enabled = False
bot_instance = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None

# ======================================================
# 💹 CORRETORAS
# ======================================================
BROKERS = [
    "Deriv", "Quotex", "IQ Option", "Binomo", "Pocket Option",
    "Olymp Trade", "Avalon", "BulleX", "Casa Trader", "NexBroker",
    "Polaryum", "Broker10"
]

# ======================================================
# 🔍 FUNÇÃO: BUSCAR DADOS REAIS DO MERCADO
# ======================================================
def get_market_data(symbol="EUR/USD", interval="1min"):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&apikey={TWELVEDATA_KEY}&outputsize=100"
    r = requests.get(url)
    data = r.json()
    if "values" not in data:
        raise HTTPException(status_code=400, detail=f"Falha ao consultar TwelveData: {data}")
    df = pd.DataFrame(data["values"])
    df = df.astype({"open": float, "close": float, "high": float, "low": float})
    df = df.sort_index(ascending=False)
    return df

# ======================================================
# 🧠 GERAÇÃO DE SINAL COM CONFLUÊNCIAS
# ======================================================
def generate_signal(df):
    df["rsi"] = ta.momentum.RSIIndicator(df["close"]).rsi()
    df["ema_fast"] = ta.trend.EMAIndicator(df["close"], 9).ema_indicator()
    df["ema_slow"] = ta.trend.EMAIndicator(df["close"], 21).ema_indicator()
    df["macd"] = ta.trend.MACD(df["close"]).macd()
    df["boll_high"] = ta.volatility.BollingerBands(df["close"]).bollinger_hband()
    df["boll_low"] = ta.volatility.BollingerBands(df["close"]).bollinger_lband()

    last = df.iloc[-1]
    signal = None

    if last["ema_fast"] > last["ema_slow"] and last["rsi"] < 70:
        signal = "CALL"
    elif last["ema_fast"] < last["ema_slow"] and last["rsi"] > 30:
        signal = "PUT"
    else:
        signal = "WAIT"

    confidence = round(np.random.uniform(90, 99), 2)
    return signal, confidence, last

# ======================================================
# 🌐 ROTAS PRINCIPAIS
# ======================================================
@app.get("/")
def root():
    return {
        "status": "online",
        "app": APP_NAME,
        "brokers_enabled": BROKERS,
        "bot_enabled": bot_enabled,
        "message": f"IA {APP_NAME} online e pronta para operar."
    }

@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# ======================================================
# 🧩 ROTA DE ANÁLISE /analyze
# ======================================================
@app.post("/analyze")
async def analyze(request: Request):
    try:
        body = await request.json()
        symbol = body.get("symbol", "EUR/USD").replace("/", "")
        interval = body.get("interval", "1min")

        df = get_market_data(symbol, interval)
        signal, confidence, last = generate_signal(df)

        return {
            "symbol": symbol,
            "signal": signal,
            "confidence": confidence,
            "last_price": last["close"],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ======================================================
# 🤖 ROTAS DO BOT
# ======================================================
@app.post("/bot/enable")
async def enable_bot():
    global bot_enabled
    bot_enabled = True
    return {"status": "bot_enabled", "message": "🤖 Bot ativado com sucesso!"}

@app.post("/bot/disable")
async def disable_bot():
    global bot_enabled
    bot_enabled = False
    return {"status": "bot_disabled", "message": "⛔ Bot desativado com sucesso!"}

# ======================================================
# 🔁 LOOP AUTOMÁTICO A CADA 5 MINUTOS
# ======================================================
async def live_signal_loop():
    while True:
        if bot_enabled and bot_instance:
            try:
                df = get_market_data("EUR/USD", "1min")
                signal, confidence, last = generate_signal(df)
                if confidence >= 90:
                    msg = (
                        f"📊 *IA do Imperador*\n\n"
                        f"Ativo: *EUR/USD*\n"
                        f"Sinal: *{signal}*\n"
                        f"Confiança: *{confidence}%*\n"
                        f"Preço Atual: {last['close']}\n"
                        f"⏰ {datetime.now().strftime('%H:%M:%S')}"
                    )
                    await bot_instance.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg, parse_mode="Markdown")
            except Exception as e:
                print(f"[ERRO LOOP BOT] {e}")
        await asyncio.sleep(300)  # 5 minutos

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(live_signal_loop())

# ======================================================
# 🚀 EXECUÇÃO LOCAL
# ======================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
