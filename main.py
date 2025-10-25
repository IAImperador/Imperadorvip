import os
import asyncio
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import aiohttp
from urllib.parse import quote

# ========================
# Config & Estado em Memória
# ========================

API_KEY = os.getenv("API_KEY", "imperadorvip-secure-key-2025")
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
MODE = os.getenv("MODE", "producao")
PORT = int(os.getenv("PORT", "8080"))

# Bot ativo por variável de ambiente (aceita "true"/"false" em PT também)
def _str_to_bool(v: str) -> bool:
    return str(v).strip().lower() in {"1", "true", "t", "yes", "y", "verdadeiro", "sim"}

BOT_ACTIVE = _str_to_bool(os.getenv("BOT_ACTIVE", "false"))

# Último sinal mantido em memória
last_signal: Dict[str, Any] = {
    "status": "aguardando",
    "sinal": {"sinal": "NEUTRO", "confianca": 0.0},
}

# ========================
# App & CORS
# ========================

app = FastAPI(title="ImperadorVIP API", version="4.0")

_allowed = os.getenv("ALLOWED_ORIGINS", "*").strip()
if _allowed == "*" or _allowed == "":
    origins = ["*"]
else:
    origins = [o.strip() for o in _allowed.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================
# Models
# ========================

class ToggleBody(BaseModel):
    active: bool = Field(..., description="Ativar (true) ou desativar (false) o bot")


class AnalysisBody(BaseModel):
    symbol: str = Field(..., description="Par para análise. Ex: 'EUR/USD'")
    interval: str = Field("1min", description="Intervalo TwelveData (ex: 1min, 5min)")
    outputsize: int = Field(12, ge=1, le=5000, description="Qtde de candles para retorno")


# ========================
# Helpers
# ========================

async def send_telegram_message(text: str) -> None:
    """Envia mensagem ao Telegram se token e chat id existirem."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, json=payload) as resp:
            # Ignora erros silenciosamente; log básico:
            _ = await resp.text()

def _calc_signal_from_ohlc(open_p: float, close_p: float) -> Dict[str, Any]:
    if close_p > open_p:
        sinal = "CALL"
    elif close_p < open_p:
        sinal = "PUT"
    else:
        sinal = "NEUTRO"

    # confiança simples baseada na variação percentual
    try:
        var_pct = abs((close_p - open_p) / open_p) * 100.0
    except ZeroDivisionError:
        var_pct = 0.0

    # limita 0..100
    confianca = max(0.0, min(100.0, var_pct * 100 / 100))  # ajuste simples
    return {"sinal": sinal, "confianca": round(confianca, 2)}

async def fetch_twelvedata_latest(symbol: str, interval: str, outputsize: int) -> Dict[str, Any]:
    if not TWELVEDATA_API_KEY:
        raise HTTPException(status_code=400, detail="TWELVEDATA_API_KEY ausente")

    # TwelveData aceita "EUR/USD"
    qs_symbol = quote(symbol, safe="")
    url = (
        "https://api.twelvedata.com/time_series"
        f"?symbol={qs_symbol}&interval={interval}&outputsize={outputsize}&apikey={TWELVEDATA_API_KEY}"
    )

    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as resp:
            data = await resp.json()
            if "status" in data and data["status"] == "error":
                raise HTTPException(status_code=400, detail=data.get("message", "Erro TwelveData"))
            values = data.get("values") or []
            if not values:
                raise HTTPException(status_code=404, detail="Sem dados retornados pela TwelveData")
            latest = values[0]
            try:
                open_p = float(latest["open"])
                close_p = float(latest["close"])
            except Exception:
                raise HTTPException(status_code=500, detail="Formato inesperado de dados TwelveData")
            return {"meta": data.get("meta", {}), "latest": latest, "open": open_p, "close": close_p}

async def analyze_and_maybe_notify(symbol: str, interval: str, outputsize: int) -> Dict[str, Any]:
    global last_signal, BOT_ACTIVE

    td = await fetch_twelvedata_latest(symbol, interval, outputsize)
    sig = _calc_signal_from_ohlc(td["open"], td["close"])

    last_signal = {"status": "ok", "sinal": sig, "meta": {"symbol": symbol, "interval": interval}}

    if BOT_ACTIVE:
        texto = (
            f"📈 <b>Análise {symbol}</b>\n"
            f"Intervalo: {interval}\n"
            f"Sinal: <b>{sig['sinal']}</b>\n"
            f"Confiança: <b>{sig['confianca']}%</b>"
        )
        # não bloqueia a resposta se o telegram falhar
        asyncio.create_task(send_telegram_message(texto))

    return last_signal

# ========================
# Rotas Básicas
# ========================

@app.get("/")
def root():
    return {"name": "ImperadorVIP API", "mode": MODE, "ok": True}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/signal/live")
def signal_live():
    return last_signal

# ========================
# Bot (Telegram)
# ========================

@app.get("/bot/status")
def bot_status():
    return {"active": BOT_ACTIVE}

@app.post("/bot/activate")
def bot_activate():
    global BOT_ACTIVE
    BOT_ACTIVE = True
    return {"active": BOT_ACTIVE}

@app.post("/bot/deactivate")
def bot_deactivate():
    global BOT_ACTIVE
    BOT_ACTIVE = False
    return {"active": BOT_ACTIVE}

@app.post("/bot/toggle")
def bot_toggle(body: ToggleBody):
    global BOT_ACTIVE
    BOT_ACTIVE = bool(body.active)
    return {"active": BOT_ACTIVE}

# ========================
# Análise (mapeia várias rotas esperadas pelo front)
# ========================

async def _analysis_handler(body: AnalysisBody):
    return await analyze_and_maybe_notify(body.symbol, body.interval, body.outputsize)

@app.post("/analysis/realtime")
async def analysis_realtime(body: AnalysisBody):
    return await _analysis_handler(body)

@app.post("/analysis")
async def analysis(body: AnalysisBody):
    return await _analysis_handler(body)

@app.post("/analyze")
async def analyze(body: AnalysisBody):
    return await _analysis_handler(body)

# ========================
# Execução local
# ========================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)
