from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ImperadorVIP Signals API", version="4.0")

# =====================================================
# 🔥 CONFIGURAÇÃO CORS (Permite conexão com Base44)
# =====================================================
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

# =====================================================
# 🌍 VARIÁVEIS E ESTADO GLOBAL
# =====================================================
BOT_ACTIVE = False
LAST_SIGNAL = {}

TWELVEDATA_KEY = os.getenv("TWELVEDATA_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# =====================================================
# 🩺 ROTAS DE STATUS
# =====================================================
@app.get("/")
def home():
    return {"status": "ok", "service": "ImperadorVIP Signals API", "time": time.strftime("%Y-%m-%dT%H:%M:%S")}

@app.get("/health")
def health_check():
    return {"status": "ok", "msg": "API funcional e operante."}

# =====================================================
# 🤖 BOT STATUS
# =====================================================
@app.post("/bot/status")
def alternar_bot(data: dict = Body(...)):
    """Ativa ou desativa o bot de envio automático"""
    global BOT_ACTIVE
    BOT_ACTIVE = data.get("ativo", False)
    return {"status": "ok", "bot_ativo": BOT_ACTIVE, "mensagem": "Bot atualizado com sucesso"}

@app.get("/bot/status")
def verificar_bot():
    return {"status": "ok", "bot_ativo": BOT_ACTIVE}

# =====================================================
# 📊 ANALISADOR DE SINAIS EM TEMPO REAL
# =====================================================
@app.post("/analyze")
def analisar(data: dict = Body(...)):
    try:
        if not TWELVEDATA_KEY:
            return {"detail": "Falta TWELVEDATA_KEY"}

        symbol = data.get("symbol", "EUR/USD").replace("/", "")
        interval = data.get("interval", "1min")

        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize=30&apikey={TWELVEDATA_KEY}"
        response = requests.get(url)
        response.raise_for_status()
        data_api = response.json()

        if "values" not in data_api:
            return {"detail": "Falha ao consultar TwelveData", "resposta": data_api}

        values = data_api["values"]
        close_prices = [float(v["close"]) for v in values[:5]]

        direcao = "CALL" if close_prices[0] < close_prices[-1] else "PUT"
        confianca = round(abs((close_prices[-1] - close_prices[0]) / close_prices[0]) * 100, 2)

        LAST_SIGNAL.update({
            "ativo": symbol,
            "sinal": direcao,
            "confianca": confianca,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })

        return {"status": "ok", "sinal": LAST_SIGNAL}

    except Exception as e:
        return {"detail": f"Erro interno: {str(e)}"}

# =====================================================
# 🔁 ENVIO AUTOMÁTICO PARA TELEGRAM (a cada 5 minutos)
# =====================================================
import threading
import time

def enviar_para_telegram():
    """Envia sinais automaticamente para o Telegram se o bot estiver ativo"""
    while True:
        if BOT_ACTIVE and LAST_SIGNAL:
            try:
                msg = f"📈 Sinal IA do Imperador\nAtivo: {LAST_SIGNAL['ativo']}\nSinal: {LAST_SIGNAL['sinal']}\nConfiabilidade: {LAST_SIGNAL['confianca']}%"
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
                requests.post(url, data=payload)
            except Exception as e:
                print(f"Erro ao enviar para Telegram: {e}")
        time.sleep(300)  # 5 minutos

threading.Thread(target=enviar_para_telegram, daemon=True).start()

# =====================================================
# 🧩 EXECUÇÃO LOCAL (debug)
# =====================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)), reload=True)
