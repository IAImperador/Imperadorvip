# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
import time
import threading

app = FastAPI(title="IA do Imperador - Sinais em Tempo Real")

# ==========================
# 🔧 Configuração do CORS
# ==========================
origins = [
    "https://app.base44.io",
    "https://studio.base44.io",
    "https://imperadorvip.base44.app",
    "https://imperadorvip-production.up.railway.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# 🔐 Variáveis de ambiente
# ==========================
API_KEY = os.getenv("API_KEY", "imperadorvip-secure-key-2025")
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PORT = int(os.getenv("PORT", 8080))

# ==========================
# 📈 Função para buscar dados do TwelveData
# ==========================
def obter_dados_twelvedata(symbol="EUR/USD", interval="1min"):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&apikey={TWELVEDATA_API_KEY}&outputsize=5"
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Falha ao consultar TwelveData")
    data = response.json()
    if "values" not in data:
        raise HTTPException(status_code=400, detail="Retorno inválido da TwelveData")
    return data["values"]

# ==========================
# 🤖 Função de análise de sinal
# ==========================
def analisar_sinal():
    dados = obter_dados_twelvedata()
    ult = float(dados[0]["close"])
    ant = float(dados[1]["close"])

    if ult > ant:
        direcao = "CALL"
    elif ult < ant:
        direcao = "PUT"
    else:
        direcao = "NEUTRO"

    variacao = abs(ult - ant) / ant * 100
    confianca = min(100, round(variacao * 25, 2))  # exemplo de cálculo
    return {"sinal": direcao, "confianca": confianca}

# ==========================
# 📡 Endpoint /analyze
# ==========================
@app.post("/analyze")
def analisar_endpoint():
    try:
        resultado = analisar_sinal()
        return {"status": "ok", "resultado": resultado}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==========================
# ⚡ Rota /signal/live (atualização automática)
# ==========================
@app.get("/signal/live")
def sinal_live():
    try:
        resultado = analisar_sinal()
        if resultado["confianca"] >= 90:
            return {"status": "ativo", "sinal": resultado}
        else:
            return {"status": "aguardando", "sinal": resultado}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================
# 🤖 Thread opcional: envio automático (futuro)
# ==========================
def loop_sinais():
    while True:
        try:
            resultado = analisar_sinal()
            if resultado["confianca"] >= 90 and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                mensagem = f"📊 Novo sinal ({resultado['confianca']}%) ➜ {resultado['sinal']}"
                requests.get(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    params={"chat_id": TELEGRAM_CHAT_ID, "text": mensagem},
                    timeout=10,
                )
        except Exception as e:
            print("Erro no loop:", e)
        time.sleep(60)  # intervalo fixo de 60s

# Iniciar thread
threading.Thread(target=loop_sinais, daemon=True).start()

# ==========================
# 🚀 Inicialização
# ==========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT)
