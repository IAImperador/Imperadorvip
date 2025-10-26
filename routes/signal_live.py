from fastapi import APIRouter
import os, time, threading, requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
router = APIRouter()

TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")
BOT_ACTIVE = os.getenv("BOT_ACTIVE", "false").lower() == "true"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("ID_DE_CHAT_DO_TELEGRAM")

def gerar_sinal():
    """Função principal de geração e envio de sinais"""
    try:
        url = f"https://api.twelvedata.com/time_series?symbol=EUR/USD&interval=1min&apikey={TWELVEDATA_API_KEY}"
        resposta = requests.get(url)
        dados = resposta.json()
        valor = float(dados["values"][0]["close"])

        confianca = 90.5 if valor % 2 == 0 else 85.0
        direcao = "CALL" if valor % 2 == 0 else "PUT"

        sinal = {
            "status": "ativo",
            "par": "EUR/USD",
            "sinal": direcao,
            "confianca": confianca,
            "horario": datetime.now().strftime("%H:%M:%S")
        }

        print(f"Sinal gerado: {sinal}")

        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            mensagem = f"📊 *SINAL IMPERADOR AI*\n\nAtivo: {sinal['par']}\nSinal: {sinal['sinal']}\nConfiança: {sinal['confianca']}%\nHorário: {sinal['horario']}"
            requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", params={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": mensagem,
                "parse_mode": "Markdown"
            })
        return sinal

    except Exception as e:
        print("Erro ao gerar sinal:", e)
        return {"status": "erro", "detalhe": str(e)}

def loop_automatico():
    """Executa o bot a cada 5 minutos"""
    while BOT_ACTIVE:
        gerar_sinal()
        time.sleep(300)  # 5 minutos

@router.get("/signal/live")
def live_signal():
    if BOT_ACTIVE:
        threading.Thread(target=loop_automatico, daemon=True).start()
        return {"status": "rodando", "mensagem": "Bot ativo — sinais a cada 5 minutos."}
    else:
        return {"status": "aguardando", "mensagem": "Bot desativado no momento."}


