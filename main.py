import os
import time
import threading
import requests
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from datetime import datetime

# ==============================
# CONFIGURAÇÕES INICIAIS
# ==============================
load_dotenv()

app = FastAPI(title="IA do Imperador 4.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variáveis de ambiente
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("ID_DE_CHAT_DO_TELEGRAM")
BOT_ACTIVE = False  # inicia desativado

# ==============================
# MODELO BASE
# ==============================
class BotStatus(BaseModel):
    ativo: bool

# ==============================
# FUNÇÃO DE GERAÇÃO DE SINAIS
# ==============================
def gerar_sinal():
    """Consulta ativos da TwelveData e gera sinal aleatório com confiança"""
    try:
        # Lista de ativos (pares de moedas e índices principais)
        ativos = [
            "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "USD/CAD", "AUD/USD",
            "NZD/USD", "EUR/JPY", "GBP/JPY", "EUR/GBP", "EUR/CHF", "AUD/JPY",
            "CAD/JPY", "NZD/JPY", "CHF/JPY", "EUR/CAD", "GBP/CAD", "AUD/CAD",
            "BTC/USD", "ETH/USD", "XAU/USD", "XAG/USD"
        ]

        # Escolhe ativo atual (exemplo rotativo)
        ativo = ativos[int(datetime.utcnow().minute) % len(ativos)]

        url = f"https://api.twelvedata.com/quote?symbol={ativo}&apikey={TWELVEDATA_API_KEY}"
        r = requests.get(url)
        data = r.json()

        if "close" not in data:
            return None

        # Exemplo de cálculo simples de confiança
        close = float(data["close"])
        open_price = float(data.get("open", close))
        variacao = ((close - open_price) / open_price) * 100
        confianca = min(abs(variacao) * 50, 100)

        if variacao > 0:
            sinal = "CALL"
        elif variacao < 0:
            sinal = "PUT"
        else:
            sinal = "NEUTRO"

        return {"ativo": ativo, "sinal": sinal, "confianca": round(confianca, 2)}

    except Exception as e:
        return {"erro": str(e)}

# ==============================
# ROTA: ANALISAR SINAL AO VIVO
# ==============================
@app.get("/signal/live")
def sinal_live():
    sinal = gerar_sinal()
    if not sinal:
        return {"detail": "Nenhum sinal disponível ainda"}
    return {"status": "ok", "sinal": sinal}

# ==============================
# ROTA: ATIVAR/DESATIVAR BOT
# ==============================
@app.post("/bot/status")
def alternar_bot(status: BotStatus):
    """Ativa/Desativa bot de envio automático"""
    global BOT_ACTIVE
    BOT_ACTIVE = status.ativo
    return {"bot_status": BOT_ACTIVE, "msg": "Bot atualizado com sucesso"}

# ==============================
# FUNÇÃO: ENVIAR PARA TELEGRAM
# ==============================
def enviar_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Erro Telegram: {e}")

# ==============================
# LOOP AUTOMÁTICO (A CADA 5 MIN)
# ==============================
def ciclo_automatico():
    global BOT_ACTIVE
    while True:
        if BOT_ACTIVE:
            sinal = gerar_sinal()
            if sinal and sinal["confianca"] >= 90:
                msg = (
                    f"🤖 <b>IA do Imperador 4.0</b>\n\n"
                    f"💱 <b>Ativo:</b> {sinal['ativo']}\n"
                    f"📈 <b>Sinal:</b> {sinal['sinal']}\n"
                    f"🎯 <b>Confiança:</b> {sinal['confianca']}%\n"
                    f"🕒 {datetime.now().strftime('%H:%M:%S')}\n"
                )
                enviar_telegram(msg)
                print(f"Sinal enviado: {sinal}")
            else:
                print("Sem sinal acima de 90%")
        time.sleep(300)  # 5 minutos

# ==============================
# THREAD DE LOOP
# ==============================
def iniciar_loop():
    t = threading.Thread(target=ciclo_automatico, daemon=True)
    t.start()

@app.on_event("startup")
def startup_event():
    print("🚀 IA do Imperador iniciada com sucesso")
    iniciar_loop()

# ==============================
# ROTA PRINCIPAL
# ==============================
@app.get("/")
def root():
    return {"status": "online", "bot": BOT_ACTIVE, "hora": datetime.now().strftime("%H:%M:%S")}
