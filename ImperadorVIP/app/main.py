from fastapi import FastAPI, Request
from app.services.signal_generator import gerar_sinal
from app.services.telegram_service import enviar_mensagem_telegram
import asyncio

app = FastAPI(title="ImperadorVIP Signals API")
BOT_ATIVO = False

@app.get("/")
def home():
    return {"status": "ok", "service": "ImperadorVIP Signals API"}

@app.get("/health")
def health():
    return {"status": "ok", "message": "Servidor ativo"}

@app.get("/signal/live")
def signal_live():
    sinal = gerar_sinal()
    if sinal:
        return {"status": "ok", "sinal": sinal}
    return {"detail": "Nenhum sinal disponível ainda"}

@app.post("/bot/status")
async def alternar_bot(request: Request):
    global BOT_ATIVO
    data = await request.json()
    BOT_ATIVO = data.get("ativo", False)
    return {"status": "ok", "bot": BOT_ATIVO}

async def ciclo_bot():
    global BOT_ATIVO
    while True:
        if BOT_ATIVO:
            sinal = gerar_sinal()
            if sinal and sinal["confianca"] >= 90:
                msg = (
                    f"🤖 *IA do Imperador 4.0*\n"
                    f"Ativo: {sinal['ativo']}\n"
                    f"Sinal: {sinal['sinal']}\n"
                    f"Confluência: {sinal['confianca']}%"
                )
                enviar_mensagem_telegram(msg)
        await asyncio.sleep(300)  # 5 min

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(ciclo_bot())
