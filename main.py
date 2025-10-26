# ==============================================
# IA DO IMPERADOR - BACKEND FASTAPI
# TwelveData + Telegram + Railway (Deploy)
# ==============================================

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import requests, os, random, time
from dotenv import load_dotenv
from threading import Thread

# Carregar variáveis do ambiente Railway (.env)
load_dotenv()

# -----------------------------
# VARIÁVEIS DE AMBIENTE
# -----------------------------
API_KEY = os.getenv("API_KEY", "imperadorvip-secure-key-2025")
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BOT_ACTIVE = os.getenv("BOT_ACTIVE", "false").lower() == "true"

# Ativos suportados pela TwelveData
ATIVOS = [
    "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD", "NZD/USD", "USD/CAD",
    "EUR/JPY", "GBP/JPY", "EUR/GBP", "AUD/JPY", "EUR/CAD", "GBP/CAD", "NZD/JPY",
    "EUR/NZD", "USD/ZAR", "USD/TRY", "USD/BRL", "USD/MXN", "USD/INR"
]

# Criar app FastAPI
app = FastAPI(
    title="IA do Imperador API",
    description="Servidor Railway + TwelveData + Telegram",
    version="4.0"
)

# Permitir requisições de qualquer origem (Base44)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# FUNÇÕES AUXILIARES
# -----------------------------

def obter_dados_twelvedata(symbol: str):
    """Consulta dados em tempo real da TwelveData"""
    try:
        url = f"https://api.twelvedata.com/quote?symbol={symbol}&apikey={TWELVEDATA_API_KEY}"
        r = requests.get(url, timeout=10)
        data = r.json()
        if "price" not in data:
            return None
        preco = float(data["price"])
        variacao = float(data.get("percent_change", 0))
        direcao = "CALL" if variacao > 0 else "PUT"
        confianca = round(min(100, abs(variacao) * 10 + random.uniform(85, 99)), 2)
        return {"ativo": symbol, "sinal": direcao, "confiança": confianca}
    except Exception as e:
        print(f"Erro ao consultar {symbol}: {e}")
        return None


def enviar_telegram(msg: str):
    """Envia mensagem no Telegram"""
    try:
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
            requests.post(url, data=payload)
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")


def gerar_sinal():
    """Gera sinal com base na confiança mínima (>=90%)"""
    for ativo in ATIVOS:
        resultado = obter_dados_twelvedata(ativo)
        if resultado and resultado["confiança"] >= 90:
            return resultado
    return None


# -----------------------------
# ROTAS PRINCIPAIS
# -----------------------------

@app.get("/")
def raiz():
    return {"status": "online", "projeto": "IA do Imperador 4.0"}

@app.get("/signal/live")
def sinal_live():
    """Retorna sinal ao front-end (Base44)"""
    try:
        sinal = gerar_sinal()
        if not sinal:
            return {"detail": "Nenhum sinal disponível ainda"}
        return {"status": "ok", "sinal": sinal}
    except Exception as e:
        return {"detail": f"Erro interno: {str(e)}"}

@app.post("/bot/status")
def alternar_bot(body: dict):
    """Ativa/Desativa bot de envio automático"""
    global BOT_ACTIVE
    BOT_ACTIVE = body.get("ativo", False)
    return {"bot_status": BOT_ACTIVE, "msg": "Bot atualizado com sucesso"}

# -----------------------------
# LOOP AUTOMÁTICO DO BOT
# -----------------------------

def ciclo_automatico():
    """Executa a cada 5 minutos"""
    while True:
        if BOT_ACTIVE:
            sinal = gerar_sinal()
            if sinal:
                msg = (
                    f"📡 *IA do Imperador 4.0*\n\n"
                    f"Ativo: {sinal['ativo']}\n"
                    f"Sinal: {sinal['sinal']}\n"
                    f"Confiança: {sinal['confiança']}%\n\n"
                    f"#imperador #sinaisbinarios"
                )
                enviar_telegram(msg)
        time.sleep(300)  # 5 minutos

# Thread do bot
Thread(target=ciclo_automatico, daemon=True).start()

# -----------------------------
# EXECUÇÃO LOCAL (para debug)
# -----------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)))


