# main.py — IA do Imperador (versão com rota /signal/live)

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import uvicorn
from routes.signal_live import router as signal_live_router  # ✅ Import da nova rota

# ========================================================
# CONFIGURAÇÃO PRINCIPAL DO APP
# ========================================================
app = FastAPI(
    title="IA do Imperador",
    description="API profissional de sinais com TwelveData + Telegram",
    version="4.0"
)

# --------------------------------------------------------
# VARIÁVEIS DE AMBIENTE
# --------------------------------------------------------
API_KEY = os.getenv("API_KEY", "imperadorvip-secure-key-2025")
APP_NAME = os.getenv("NOME_DO_APLICATIVO", "ImperadorVIP")
TWELVEDATA_KEY = os.getenv("TWELVEDATA_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("ID_DE_CHAT_DO_TELEGRAM", "@IAdoimperador")
PORT = int(os.getenv("PORTA", 8080))
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")

# --------------------------------------------------------
# CONFIGURAÇÃO DE CORS
# --------------------------------------------------------
if ALLOWED_ORIGINS == "*":
    origins = ["*"]
else:
    origins = [o.strip() for o in ALLOWED_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================================================
# ROTAS PRINCIPAIS
# ========================================================

@app.get("/")
async def root():
    """Status geral do servidor"""
    return {
        "status": "online",
        "app": APP_NAME,
        "message": f"Servidor {APP_NAME} ativo e pronto para sinais ao vivo!"
    }


@app.get("/status")
async def status_check():
    """Verifica status geral da API"""
    return {
        "API_KEY": "Configurada" if API_KEY else "Faltando",
        "TWELVEDATA_KEY": "Configurada" if TWELVEDATA_KEY else "Faltando",
        "BOT_TOKEN": "Configurado" if BOT_TOKEN else "Faltando",
        "CHAT_ID": CHAT_ID,
        "PORT": PORT,
    }


@app.post("/analyze")
async def analyze(request: Request):
    """Análise rápida EUR/USD"""
    data = await request.json()
    symbol = data.get("symbol", "EUR/USD")
    interval = data.get("interval", "1min")

    if not TWELVEDATA_KEY:
        raise HTTPException(status_code=400, detail="Falta TWELVEDATA_KEY")

    import requests
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&apikey={TWELVEDATA_KEY}&outputsize=2"
    r = requests.get(url)
    if r.status_code != 200:
        raise HTTPException(status_code=400, detail="Falha ao consultar TwelveData")

    json_data = r.json()
    if "values" not in json_data:
        raise HTTPException(status_code=400, detail="Dados insuficientes")

    last = float(json_data["values"][0]["close"])
    prev = float(json_data["values"][1]["close"])

    direction = "CALL" if last > prev else "PUT"
    confidence = abs((last - prev) / prev * 100)

    return {
        "symbol": symbol,
        "direction": direction,
        "confidence": round(confidence, 2),
        "last_price": last,
        "previous_price": prev,
    }

# ========================================================
# INCLUIR ROTAS EXTERNAS (como /signal/live)
# ========================================================
app.include_router(signal_live_router)

# ========================================================
# HANDLER GLOBAL DE ERROS
# ========================================================
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Erro interno: {str(exc)}"},
    )

# ========================================================
# EXECUÇÃO LOCAL (Railway usa este arquivo automaticamente)
# ========================================================
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT)
