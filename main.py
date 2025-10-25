import os
import time
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from threading import Thread
from datetime import datetime
import random

# ==============================
# VARIÁVEIS DE AMBIENTE
# ==============================
API_KEY = os.getenv("API_KEY", "imperadorvip-secure-key-2025")
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("ID_DE_CHAT_DO_TELEGRAM", "")
BOT_ACTIVE = os.getenv("BOT_ACTIVE", "false").lower() == "true"
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# ==============================
# CONFIGURAÇÃO DO FASTAPI
# ==============================
app = FastAPI(title="IA do Imperador", version="4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================
# FUNÇÃO DE ANÁLISE (EXEMPLO)
# ==============================
def gerar_sinal_reversao(symbol="EUR/USD"):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&apikey={TWELVEDATA_API_KEY}&outputsize=30"
        resp = requests.get(url)
        data = resp.json()

        if "values" not in data:
            raise ValueError(data.get("message", "Erro na resposta TwelveData"))

        candles = data["values"][:5]
        closes = [float(c["close"]) for c in candles]
        opens = [float(c["open"]) for c in candles]

        tendencia = "CALL" if closes[0] < closes[-1] else "PUT"
        confianca = round(random.uniform(85, 99), 2)

        if confianca < 90:
            return {"sinal": "NEUTRO", "confianca": confianca}

        return {"sinal": tendencia, "confianca": confianca}

    except Exception as e:
        return {"erro": str(e)}

# ==============================
# FUNÇÃO PARA ENVIAR TELEGRAM
# ==============================
def enviar_telegram(msg):
    if not BOT_ACTIVE or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
        requests.post(url, json=payload)
    except Exception as e:
        print(f"[ERRO TELEGRAM] {e}")

# ==============================
# ROTA DE TESTE / STATUS
# ==============================
@app.get("/")
def home():
    return {"status": "ativo", "versao": "4.0"}

# ==============================
# ROTA DE ANÁLISE /signal/live
# ==============================
@app.get("/signal/live")
def sinal_live():
    try:
        sinal = gerar_sinal_reversao()

        if "erro" in sinal:
            raise HTTPException(status_code=400, detail=sinal["erro"])

        if sinal["sinal"] in ["CALL", "PUT"] and sinal["confianca"] >= 90:
            msg = f"🔥 Sinal {sinal['sinal']} ({sinal['confianca']}%) - {datetime.now().strftime('%H:%M:%S')}"
            enviar_telegram(msg)
            return {"status": "ok", "sinal": sinal}

        return {"status": "aguardando", "sinal": sinal}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================
# THREAD AUTOMÁTICA (loop 60s)
# ==============================
def loop_analise_automatica():
    while True:
        try:
            sinal = gerar_sinal_reversao()
            if sinal["sinal"] in ["CALL", "PUT"] and sinal["confianca"] >= 90:
                msg = f"🤖 [Imperador AI] Sinal {sinal['sinal']} ({sinal['confianca']}%) - {datetime.now().strftime('%H:%M:%S')}"
                enviar_telegram(msg)
            time.sleep(60)
        except Exception as e:
            print(f"[ERRO LOOP] {e}")
            time.sleep(60)

# ==============================
# EXECUÇÃO PRINCIPAL
# ==============================
if __name__ == "__main__":
    import uvicorn
    if BOT_ACTIVE:
        Thread(target=loop_analise_automatica, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORTA", 8080)))

