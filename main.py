from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
import asyncio
import aiohttp
from telegram import Bot

# Carregar variáveis de ambiente do Railway
PORT = os.getenv("PORT", "8080")
APP_NAME = os.getenv("APP_NAME", "ImperadorVIP")
API_KEY = os.getenv("API_KEY", "imperadorvip-secure-key-2025")
TWELVEDATA_KEY = os.getenv("TWELVEDATA_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BROKERS_ENABLED = os.getenv("BROKERS_ENABLED", "")
BOT_ACTIVE = os.getenv("BOT_ACTIVE", "false").lower() == "true"
MODE = os.getenv("MODE", "production")

app = FastAPI(title=f"{APP_NAME} - IA do Imperador")

# Configuração do CORS
origins = [
    "https://imperadorvip.base44.app",
    "https://app.base44.io",
    "https://studio.base44.io",
    "https://base44.app",
    "https://imperadorvip-production.up.railway.app",
    "*",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Função para enviar mensagem no Telegram
async def send_telegram_message(text: str):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            bot = Bot(token=TELEGRAM_BOT_TOKEN)
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text)
        except Exception as e:
            print(f"Erro ao enviar mensagem Telegram: {e}")

# Status da API
@app.get("/")
async def root():
    return {
        "status": "online",
        "app": APP_NAME,
        "message": f"{APP_NAME} ativo e pronto para sinais reais.",
        "bot_active": BOT_ACTIVE,
    }

# Endpoint para testar análise TwelveData
@app.get("/analyze")
async def analyze(symbol: str = "EUR/USD"):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&apikey={TWELVEDATA_KEY}&outputsize=5"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                if "values" not in data:
                    return {"detail": "Erro na API TwelveData", "response": data}
                candles = data["values"][:5]
                msg = f"🔍 Análise {symbol}\nÚltimas velas:\n" + "\n".join(
                    [f"🕐 {c['datetime']} | 💰 {c['close']}" for c in candles]
                )
                if BOT_ACTIVE:
                    await send_telegram_message(msg)
                return {"status": "ok", "symbol": symbol, "data": candles}
    except Exception as e:
        return {"detail": f"Falha ao consultar TwelveData: {e}"}

# Endpoint para alternar o estado do bot
@app.post("/toggle-bot")
async def toggle_bot():
    global BOT_ACTIVE
    BOT_ACTIVE = not BOT_ACTIVE
    status = "ATIVADO ✅" if BOT_ACTIVE else "DESATIVADO ❌"
    msg = f"🤖 Bot Telegram {status} para {APP_NAME}."
    if BOT_ACTIVE:
        await send_telegram_message(msg)
    return {"bot_active": BOT_ACTIVE, "message": msg}

# Executar servidor local (Railway usa porta automática)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(PORT))
