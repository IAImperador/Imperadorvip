from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx, asyncio, os, time
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="IA do Imperador – Live Signals")

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Variáveis de ambiente
API_KEY = os.getenv("API_KEY")
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BOT_ACTIVE = os.getenv("BOT_ACTIVE", "false").lower() == "true"

# Lista de ativos padrão (pode ser expandida com todos os disponíveis)
ATIVOS = [
    "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "USD/CAD",
    "AUD/USD", "NZD/USD", "EUR/JPY", "GBP/JPY", "EUR/GBP",
    "EUR/CAD", "EUR/AUD", "NZD/JPY", "CAD/JPY", "AUD/JPY",
    "USD/BRL", "USD/MXN", "USD/ZAR", "USD/TRY", "USD/INR",
    "USD/PHP", "USD/NGN", "USD/ARS", "USD/IDR", "USD/EGP"
]

ULTIMO_SINAL = None

async def buscar_dados_twelvedata(ativo):
    url = f"https://api.twelvedata.com/time_series?symbol={ativo}&interval=1min&outputsize=5&apikey={TWELVEDATA_API_KEY}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url)
            dados = r.json()
            return dados
    except Exception as e:
        return {"error": str(e)}

def analisar_dados(dados):
    if "values" not in dados:
        return {"sinal": "NEUTRO", "confianca": 0.0}
    valores = dados["values"]
    if len(valores) < 3:
        return {"sinal": "NEUTRO", "confianca": 0.0}

    # Análise simples — exemplo
    ult = float(valores[0]["close"])
    penult = float(valores[1]["close"])
    antepen = float(valores[2]["close"])

    if ult > penult > antepen:
        return {"sinal": "CALL", "confianca": 92.5}
    elif ult < penult < antepen:
        return {"sinal": "PUT", "confianca": 91.3}
    else:
        return {"sinal": "NEUTRO", "confianca": 70.0}

async def enviar_telegram(msg):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
    async with httpx.AsyncClient() as client:
        await client.post(url, data=payload)

@app.get("/signal/live")
async def sinal_live():
    global ULTIMO_SINAL
    melhores = []

    for ativo in ATIVOS:
        dados = await buscar_dados_twelvedata(ativo)
        resultado = analisar_dados(dados)
        if resultado["confianca"] >= 90:
            melhores.append((ativo, resultado))

    if melhores:
        ativo, sinal = max(melhores, key=lambda x: x[1]["confianca"])
        ULTIMO_SINAL = {"ativo": ativo, **sinal}
        return {"status": "ok", "sinal": ULTIMO_SINAL}
    else:
        return {"detail": "Nenhum sinal disponível ainda"}

async def loop_envio_sinais():
    while True:
        if BOT_ACTIVE:
            resposta = await sinal_live()
            if "sinal" in resposta and resposta["sinal"]["confianca"] >= 90:
                msg = f"📊 Sinal {resposta['sinal']['sinal']} – {resposta['sinal']['confianca']}% de confiança"
                await enviar_telegram(msg)
        await asyncio.sleep(300)  # 5 minutos

@app.on_event("startup")
async def iniciar():
    asyncio.create_task(loop_envio_sinais())
