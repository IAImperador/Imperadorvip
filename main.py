from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import requests, os, time, threading

app = FastAPI()

# ---------------------------
# 🔧 Configurações
# ---------------------------
API_KEY = os.getenv("API_KEY", "")
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("ID_DE_CHAT_DO_TELEGRAM", "")
BOT_ACTIVE = False
MIN_CONFIDENCE = 90.0

# ---------------------------
# 🚪 CORS
# ---------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# ⚡ Função de gerar sinal
# ---------------------------
def gerar_sinal():
    try:
        pair = "USD/JPY"
        url = f"https://api.twelvedata.com/ema?symbol={pair.replace('/', '')}&interval=1min&apikey={TWELVEDATA_API_KEY}"
        r = requests.get(url).json()

        ema = float(r.get("values", [{}])[0].get("ema", 0))
        price = float(r.get("meta", {}).get("symbol", "0").replace("/", "")) if "meta" in r else 0

        # Mock de decisão (você pode mudar lógica real)
        confianca = round(90 + (time.time() % 10), 2)
        direcao = "PUT" if confianca % 2 == 0 else "CALL"

        if confianca >= MIN_CONFIDENCE:
            return {"ativo": pair, "sinal": direcao, "confianca": confianca}
        return None
    except Exception as e:
        return None

# ---------------------------
# 🤖 Função do Bot Telegram
# ---------------------------
def enviar_telegram(msg):
    try:
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
            requests.post(url, data=data)
    except:
        pass

# ---------------------------
# 🔁 Loop Automático do Bot
# ---------------------------
def ciclo_bot():
    while True:
        if BOT_ACTIVE:
            sinal = gerar_sinal()
            if sinal:
                msg = (
                    f"🤖 *IA do Imperador 4.0*\n\n"
                    f"Ativo: {sinal['ativo']}\n"
                    f"Sinal: {sinal['sinal']}\n"
                    f"Confiança: {sinal['confianca']}%\n"
                )
                enviar_telegram(msg)
            time.sleep(300)  # a cada 5 minutos
        else:
            time.sleep(10)

threading.Thread(target=ciclo_bot, daemon=True).start()

# ---------------------------
# 🌐 Rotas
# ---------------------------
@app.get("/")
def home():
    return {"status": "ok", "msg": "API IA do Imperador ativa"}

@app.get("/signal/live")
def signal_live():
    sinal = gerar_sinal()
    if not sinal:
        return {"detail": "Nenhum sinal disponível ainda"}
    return {"status": "ok", "sinal": sinal}

@app.post("/bot/status")
def toggle_bot(status: dict):
    global BOT_ACTIVE
    BOT_ACTIVE = status.get("ativo", False)
    return {"bot_status": BOT_ACTIVE, "msg": "Bot atualizado com sucesso"}

@app.get("/bot/status")
def bot_status():
    return {"bot_status": BOT_ACTIVE}

@app.get("/health")
def health():
    return {"status": "running", "bot": BOT_ACTIVE}
