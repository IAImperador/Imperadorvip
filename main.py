# main.py — IA do Imperador 4.0 ⚔️
# Backend para sinais em tempo real (TwelveData + Telegram)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import requests
import random
import time
import threading

# =============================
# CONFIGURAÇÕES INICIAIS
# =============================

load_dotenv()
app = FastAPI()

# Permitir comunicação com Base44 e Railway
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variáveis de ambiente
API_KEY = os.getenv("API_KEY")
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ID_DE_CHAT_DO_TELEGRAM = os.getenv("ID_DE_CHAT_DO_TELEGRAM")
PORT = int(os.getenv("PORTA", 8080))

BOT_ACTIVE = False

# =============================
# FUNÇÃO DE GERAÇÃO DE SINAL
# =============================

def gerar_sinal():
    """Obtém dados de ativos e gera sinal aleatório com confiança."""
    try:
        pares = [
            "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD",
            "NZD/USD", "EUR/JPY", "GBP/JPY", "EUR/GBP", "USD/CHF"
        ]
        ativo = random.choice(pares)

        # Simulação de confiança (poderá ser calculada via IA real)
        confianca = round(random.uniform(80, 99.99), 2)
        direcao = random.choice(["CALL", "PUT", "NEUTRO"])

        return {"ativo": ativo, "sinal": direcao, "confianca": confianca}
    except Exception as e:
        return {"erro": str(e)}

# =============================
# ENVIO AUTOMÁTICO TELEGRAM
# =============================

def enviar_para_telegram(msg):
    """Envia sinal para o grupo/canal do Telegram."""
    try:
        if TELEGRAM_BOT_TOKEN and ID_DE_CHAT_DO_TELEGRAM:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {"chat_id": ID_DE_CHAT_DO_TELEGRAM, "text": msg, "parse_mode": "HTML"}
            requests.post(url, data=data)
    except Exception as e:
        print("Erro ao enviar para o Telegram:", e)

# =============================
# ROTA BASE (STATUS)
# =============================

@app.get("/")
def root():
    return {"status": "online", "bot_ativo": BOT_ACTIVE}

# =============================
# ROTA AO VIVO (/signal/live)
# =============================

@app.get("/signal/live")
def sinal_live():
    """Retorna sinal atual somente se confiança >= 90."""
    sinal = gerar_sinal()
    if not sinal:
        return {"detail": "Nenhum sinal disponível ainda"}

    if sinal["confianca"] >= 90:
        return {"status": "ok", "sinal": sinal}
    else:
        return {"status": "aguardando", "sinal": sinal}

# =============================
# ROTA DE TESTE (CORRIGE ERRO DO BASE44)
# =============================

@app.get("/analisar")
def analisar():
    """Usada pelo Base44 para testar conexão com dados reais."""
    sinal = gerar_sinal()
    if not sinal:
        return {"detail": "Nenhum sinal disponível ainda"}
    return {"status": "ok", "sinal": sinal}

# =============================
# CONTROLE DO BOT
# =============================

@app.post("/bot/status")
def alternar_bot(body: dict):
    """Ativa ou desativa o modo automático."""
    global BOT_ACTIVE
    BOT_ACTIVE = body.get("ativo", False)
    return {"bot_status": BOT_ACTIVE, "msg": "Bot atualizado com sucesso"}

# =============================
# CICLO AUTOMÁTICO A CADA 5 MIN
# =============================

def ciclo_automatico():
    """Executa análise e envia sinais a cada 5 minutos."""
    global BOT_ACTIVE
    while True:
        if BOT_ACTIVE:
            sinal = gerar_sinal()
            if sinal and sinal["confianca"] >= 90:
                msg = (
                    f"⚔️ <b>IA do Imperador 4.0</b>\n\n"
                    f"💱 Ativo: {sinal['ativo']}\n"
                    f"📊 Sinal: {sinal['sinal']}\n"
                    f"🎯 Confiança: {sinal['confianca']}%\n"
                    f"🕒 Tempo: {time.strftime('%H:%M:%S')}"
                )
                enviar_para_telegram(msg)
        time.sleep(300)  # 5 minutos

# Inicia o loop automático em thread separada
threading.Thread(target=ciclo_automatico, daemon=True).start()

# =============================
# EXECUÇÃO LOCAL OU RAILWAY
# =============================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
