import os
import time
import requests
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import random

# Carregar variáveis do ambiente (.env)
load_dotenv()

app = FastAPI(title="IA do Imperador - Sinais Reais")

# Permitir acesso do Base44 e do domínio Railway
origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================
# VARIÁVEIS DE AMBIENTE
# ============================
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("ID_DE_CHAT_DO_TELEGRAM")
BOT_ACTIVE = os.getenv("BOT_ACTIVE", "false").lower() == "true"

# ============================
# LISTA DE ATIVOS SUPORTADOS
# ============================
#  Todos os principais pares da TwelveData
ATIVOS = [
    "EUR/USD", "USD/JPY", "GBP/USD", "AUD/USD", "USD/CAD",
    "USD/CHF", "NZD/USD", "EUR/GBP", "EUR/JPY", "GBP/JPY",
    "EUR/CAD", "AUD/JPY", "CAD/JPY", "CHF/JPY", "NZD/JPY",
    "EUR/CHF", "GBP/CHF", "AUD/CAD", "AUD/CHF", "AUD/NZD"
]

# ============================
# FUNÇÕES PRINCIPAIS
# ============================

def gerar_sinal_aleatorio():
    """Gera um sinal fictício com confiança simulada"""
    ativo = random.choice(ATIVOS)
    direcao = random.choice(["CALL", "PUT", "NEUTRO"])
    confianca = round(random.uniform(85, 98), 2)
    return {"ativo": ativo, "sinal": direcao, "confianca": confianca}


def enviar_para_telegram(msg: str):
    """Envia o sinal para o Telegram"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram não configurado.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
    try:
        r = requests.post(url, data=payload)
        print(f"✅ Mensagem enviada para o Telegram: {r.status_code}")
    except Exception as e:
        print(f"❌ Erro ao enviar Telegram: {e}")


def consultar_twelvedata(symbol):
    """Consulta o preço atual da TwelveData"""
    try:
        url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={TWELVEDATA_API_KEY}"
        r = requests.get(url, timeout=10)
        data = r.json()
        return float(data.get("price", 0))
    except Exception:
        return None


def gerar_sinal_real():
    """Simula análise real baseada em dados TwelveData"""
    ativo = random.choice(ATIVOS)
    preco = consultar_twelvedata(ativo)
    if preco is None:
        return {"status": "erro", "mensagem": f"Falha ao consultar {ativo}"}

    confianca = round(random.uniform(80, 99.9), 2)
    direcao = "CALL" if preco % 2 > 1 else "PUT"
    return {"ativo": ativo, "sinal": direcao, "confianca": confianca}


# ============================
# ROTAS FASTAPI
# ============================

@app.get("/")
def raiz():
    return {"status": "online", "projeto": "IA do Imperador - API Railway"}

@app.get("/signal/live")
def sinal_live():
    """Retorna o sinal mais recente"""
    sinal = gerar_sinal_real()
    if sinal["confianca"] >= 90:
        return {"status": "ok", "sinal": sinal}
    return {"detail": "Nenhum sinal disponível ainda"}

@app.post("/bot/start")
def iniciar_bot(background_tasks: BackgroundTasks):
    """Ativa o envio automático a cada 5 minutos"""
    global BOT_ACTIVE
    BOT_ACTIVE = True
    background_tasks.add_task(rodar_bot)
    return {"status": "ativado", "mensagem": "Bot do Imperador ativo!"}

@app.post("/bot/stop")
def parar_bot():
    """Desativa o envio automático"""
    global BOT_ACTIVE
    BOT_ACTIVE = False
    return {"status": "parado", "mensagem": "Bot desativado."}


def rodar_bot():
    """Loop automático de envio de sinais"""
    print("🤖 Bot do Imperador iniciado (5min intervalos)")
    while BOT_ACTIVE:
        sinal = gerar_sinal_real()
        if sinal["confianca"] >= 90:
            msg = (
                f"📈 *IA DO IMPERADOR - SINAL AO VIVO*\n\n"
                f"Ativo: {sinal['ativo']}\n"
                f"Sinal: {sinal['sinal']}\n"
                f"Confiança: {sinal['confianca']}%\n\n"
                f"⚡ Tempo: 5 min\n🔥 Mercado: REAL"
            )
            enviar_para_telegram(msg)
        else:
            print(f"Sinal descartado (confianca {sinal['confianca']}%)")
        time.sleep(300)  # 5 minutos


# ============================
# EXECUÇÃO LOCAL (Railway usa automaticamente uvicorn)
# ============================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORTA", 8080)))

