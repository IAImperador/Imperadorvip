from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import requests
import asyncio
import threading
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ImperadorVIP Signals API", version="4.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variáveis
TWELVEDATA_KEY = os.getenv("TWELVEDATA_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BOT_ACTIVE = False
ULTIMO_SINAL = None


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "ImperadorVIP Signals API",
        "time": datetime.utcnow().isoformat()
    }


@app.get("/signal/live")
def signal_live():
    """Retorna o último sinal gerado"""
    if not ULTIMO_SINAL:
        raise HTTPException(status_code=404, detail="Nenhum sinal disponível ainda")
    return {"status": "ok", "sinal": ULTIMO_SINAL}


@app.post("/bot/status")
def toggle_bot(data: dict):
    """Ativa/Desativa o bot automático"""
    global BOT_ACTIVE
    BOT_ACTIVE = data.get("ativo", False)
    return {"status": "ok", "bot_ativo": BOT_ACTIVE}


async def gerar_sinal():
    """Simula geração de sinal real com confiança >90%"""
    import random
    ativos = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/CHF", "NZD/JPY", "EUR/GBP"]
    ativo = random.choice(ativos)
    direcao = random.choice(["CALL", "PUT"])
    confianca = round(random.uniform(90.0, 99.9), 2)
    return {"ativo": ativo, "sinal": direcao, "confianca": confianca}


async def enviar_telegram(mensagem: str):
    """Envia mensagem ao Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram não configurado.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Erro Telegram: {e}")


async def ciclo_bot():
    """Loop automático a cada 5 minutos"""
    global ULTIMO_SINAL
    while True:
        if BOT_ACTIVE:
            ULTIMO_SINAL = await gerar_sinal()
            msg = (
                f"🤖 *IA do Imperador 4.0*\n"
                f"Ativo: {ULTIMO_SINAL['ativo']}\n"
                f"Sinal: {ULTIMO_SINAL['sinal']}\n"
                f"Confiança: {ULTIMO_SINAL['confianca']}%\n"
                f"Horário: {datetime.now().strftime('%H:%M:%S')}"
            )
            await enviar_telegram(msg)
            print(f"SINAL ENVIADO: {ULTIMO_SINAL}")
        await asyncio.sleep(300)


def iniciar_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(ciclo_bot())


threading.Thread(target=iniciar_loop, daemon=True).start()

async def startup_event():
    asyncio.create_task(ciclo_bot())
