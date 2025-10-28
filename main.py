from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
import os
import requests
import time
import threading
from dotenv import load_dotenv

# =====================================================
# 🔧 CONFIGURAÇÃO INICIAL
# =====================================================
load_dotenv()
app = FastAPI(title="ImperadorVIP AI", version="5.0")

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
# 🌍 VARIÁVEIS DE AMBIENTE
# =====================================================
TWELVEDATA_KEY = os.getenv("TWELVEDATA_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BOT_ACTIVE = False
LAST_SIGNAL = {}

# =====================================================
# 🩺 STATUS BÁSICO
# =====================================================
@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "ImperadorVIP",
        "bot_active": BOT_ACTIVE,
        "time": time.strftime("%Y-%m-%d %H:%M:%S")
    }

# =====================================================
# 🤖 BOT - ATIVAR / DESATIVAR
# =====================================================
@app.post("/bot/toggle")
def toggle_bot(data: dict = Body(...)):
    global BOT_ACTIVE
    BOT_ACTIVE = bool(data.get("active", False))
    return {"status": "ok", "bot_active": BOT_ACTIVE, "message": "Bot status atualizado com sucesso"}

@app.get("/bot/status")
def bot_status():
    return {"status": "ok", "bot_active": BOT_ACTIVE}

# =====================================================
# 📈 FUNÇÃO DE ANÁLISE DE MERCADO (SINAIS)
# =====================================================
@app.post("/analyze")
def analyze(data: dict = Body(...)):
    try:
        if not TWELVEDATA_KEY:
            return {"detail": "Falta TWELVEDATA_KEY"}

        symbol = data.get("symbol", "EUR/USD").replace("/", "")
        interval = data.get("interval", "1min")

        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize=20&apikey={TWELVEDATA_KEY}"
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        js = res.json()

        if "values" not in js:
            return {"detail": "Falha ao consultar TwelveData", "resposta": js}

        values = js["values"]
        closes = [float(v["close"]) for v in values[:5]]

        trend = "CALL" if closes[-1] > closes[0] else "PUT"
        confidence = round(abs((closes[-1] - closes[0]) / closes[0]) * 100, 2)

        LAST_SIGNAL.update({
            "symbol": symbol,
            "signal": trend,
            "confidence": confidence,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })

        return {
            "status": "ok",
            "symbol": symbol,
            "signal": trend,
            "confidence": confidence,
            "timestamp": LAST_SIGNAL["timestamp"]
        }

    except Exception as e:
        return {"detail": f"Erro interno: {str(e)}"}

# =====================================================
# 🔁 ENVIO AUTOMÁTICO AO TELEGRAM (A CADA 5 MIN)
# =====================================================
def auto_signal_sender():
    while True:
        try:
            if BOT_ACTIVE and LAST_SIGNAL:
                conf = LAST_SIGNAL.get("confidence", 0)
                if conf >= 90:
                    msg = (
                        f"🤖 *IA do Imperador – Sinal Automático*\n\n"
                        f"📊 Ativo: {LAST_SIGNAL['symbol']}\n"
                        f"📈 Sinal: {LAST_SIGNAL['signal']}\n"
                        f"🎯 Confiabilidade: {conf}%\n"
                        f"🕒 Horário: {LAST_SIGNAL['timestamp']}"
                    )
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                        data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
                    )
            time.sleep(300)  # 5 minutos
        except Exception as e:
            print(f"Erro no loop Telegram: {e}")

threading.Thread(target=auto_signal_sender, daemon=True).start()

# =====================================================
# 🧩 EXECUÇÃO LOCAL
# =====================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)), reload=True)
