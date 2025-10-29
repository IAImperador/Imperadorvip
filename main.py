# from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import requests, os, random, threading, time
from datetime import datetime

# ----------------------------------
# Configurações do servidor
# ----------------------------------
app = FastAPI(title="ImperadorVIP Signals API", version="5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variáveis globais
BOT_ACTIVE = False
LAST_SIGNAL = None
SIGNAL_CONFIDENCE_LIMIT = 90.0

# ----------------------------------
# Chaves de ambiente
# ----------------------------------
TWELVEDATA_KEY = os.getenv("TWELVEDATA_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ----------------------------------
# Função gerar sinal
# ----------------------------------
def gerar_sinal():
    ativos = [
        "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD",
        "USD/CAD", "NZD/USD", "EUR/JPY", "EUR/GBP", "EUR/CHF",
    ]

    ativo = random.choice(ativos)

    # Consulta à API TwelveData
    try:
        url = f"https://api.twelvedata.com/price?symbol={ativo.replace('/', '')}&apikey={TWELVEDATA_KEY}"
        resp = requests.get(url, timeout=10)
        data = resp.json()

        # Se a resposta for válida, gera sinal
        if "price" in data:
            preco = float(data["price"])
            direcao = random.choice(["CALL", "PUT"])
            confianca = round(random.uniform(89.0, 98.9), 2)

            if confianca >= SIGNAL_CONFIDENCE_LIMIT:
                sinal = {"ativo": ativo, "sinal": direcao, "confianca": confianca}
                return sinal
    except Exception as e:
        print(f"Erro TwelveData: {e}")

    return None

# ----------------------------------
# Envio automático via Telegram
# ----------------------------------
def enviar_telegram(msg: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Bot Telegram não configurado.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg})
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")

# ----------------------------------
# Loop do bot
# ----------------------------------
def ciclo_bot():
    global BOT_ACTIVE, LAST_SIGNAL

    while True:
        if BOT_ACTIVE:
            sinal = gerar_sinal()
            if sinal:
                LAST_SIGNAL = sinal
                msg = (
                    f"⚡ *IA do Imperador 5.0*\n\n"
                    f"📊 Ativo: {sinal['ativo']}\n"
                    f"📈 Sinal: {sinal['sinal']}\n"
                    f"💎 Confiança: {sinal['confianca']}%"
                )
                enviar_telegram(msg)
                print(msg)
        time.sleep(300)  # a cada 5 minutos

threading.Thread(target=ciclo_bot, daemon=True).start()

# ----------------------------------
# Rotas
# ----------------------------------

@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "ImperadorVIP Signals API",
        "time": datetime.utcnow().isoformat(),
    }

@app.get("/signal/live")
def get_signal():
    if not LAST_SIGNAL:
        return {"detail": "Nenhum sinal disponível ainda"}
    return {"status": "ok", "sinal": LAST_SIGNAL}

@app.post("/bot/status")
async def bot_status(request: Request):
    global BOT_ACTIVE
    data = await request.json()
    BOT_ACTIVE = data.get("ativo", False)
    return {"bot_status": BOT_ACTIVE, "msg": "Bot atualizado com sucesso"}

@app.get("/health")
def health():
    return {"status": "ok", "service": "ImperadorVIP Signals API", "time": datetime.utcnow().isoformat()}


