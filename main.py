import os
import asyncio
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

import httpx
import pandas as pd
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------
# Config & Estado em memória
# ---------------------------
app = FastAPI(title="ImperadorVIP Signals API", version="4.0")

# CORS – evita "Failed to fetch" no Base44
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TWELVEDATA_KEY = os.getenv("TWELVEDATA_KEY") or os.getenv("TWELVEDATA_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Threshold default (pode mudar pelo body em /analisar)
CONF_MIN_DEFAULT = 90.0

# Controle do bot e último sinal
BOT_ACTIVE: bool = False
LAST_SIGNAL: Optional[Dict[str, Any]] = None
LAST_SIGNAL_AT: Optional[datetime] = None

# Task de loop
_loop_task: Optional[asyncio.Task] = None
_stop_event: asyncio.Event = asyncio.Event()

# Lista ampla de símbolos (você pode aumentar à vontade; TwelveData aceita diversos)
DEFAULT_SYMBOLS: List[str] = [
    # Forex majors
    "EUR/USD", "USD/JPY", "GBP/USD", "USD/CHF", "AUD/USD", "USD/CAD", "NZD/USD",
    "EUR/JPY", "GBP/JPY", "EUR/GBP",
    # Metais e energia (se plano permitir)
    "XAU/USD", "XAG/USD", "UKOIL/USD", "WTI/USD",
    # Índices (se plano permitir)
    "US30", "US500", "NAS100", "DE30",
]

# ---------------------------
# Helpers
# ---------------------------

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

def _safe_float(x, default: float = float("nan")) -> float:
    try:
        return float(x)
    except Exception:
        return default

async def fetch_timeseries(symbol: str, interval: str = "1min", outputsize: int = 150) -> pd.DataFrame:
    """
    Baixa candles da TwelveData e retorna DataFrame com colunas: datetime, open, high, low, close, volume
    """
    if not TWELVEDATA_KEY:
        raise RuntimeError("TWELVEDATA_KEY não configurada")

    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": str(outputsize),
        "format": "JSON",
        "apikey": TWELVEDATA_KEY,
    }
    url = "https://api.twelvedata.com/time_series"

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(url, params=params)
        data = r.json()

    # Erros da API
    if isinstance(data, dict) and "status" in data and data.get("status") == "error":
        # Ex: {"status":"error","code":"400","message":"Symbol not found"}
        raise RuntimeError(f"TwelveData error for {symbol}: {data.get('message')}")
    if "values" not in data:
        raise RuntimeError(f"TwelveData resposta inesperada para {symbol}: {data}")

    # Monta DataFrame
    df = pd.DataFrame(data["values"])
    # Normaliza tipos
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # Datas
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)

    return df

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

    rs = avg_gain / (avg_loss.replace(0, 1e-12))
    rsi_val = 100 - (100 / (1 + rs))
    return rsi_val

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def sinal_from_indicators(symbol: str, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    Gera sinal simples com EMA(9), EMA(21) e RSI(14).
    Regras:
    - EMA9 > EMA21 e RSI 55..70 => CALL
    - EMA9 < EMA21 e RSI 30..45 => PUT
    - Caso contrário => NEUTRO (descarta)
    Confiança mistura distância das EMAs e distância do RSI de 50.
    """
    if df is None or df.empty or len(df) < 50:
        return None

    df = df.copy()
    df["ema9"] = ema(df["close"], 9)
    df["ema21"] = ema(df["close"], 21)
    df["rsi14"] = rsi(df["close"], 14)

    row = df.iloc[-1]
    price = _safe_float(row["close"])
    e9 = _safe_float(row["ema9"])
    e21 = _safe_float(row["ema21"])
    r = _safe_float(row["rsi14"])

    if any(math.isnan(v) for v in [price, e9, e21, r]):
        return None

    direction = "NEUTRO"
    # Score por EMAs
    ema_gap = abs(e9 - e21) / price  # gap relativo
    ema_score = min(1.0, ema_gap * 100)  # cap

    # Score por RSI
    rsi_dev = abs(r - 50) / 50.0  # 0..1
    rsi_score = min(1.0, rsi_dev)

    # Base: mistura 50/50
    confidence = (ema_score * 50.0) + (rsi_score * 50.0)
    confidence = max(0.0, min(99.9, confidence))

    # Direção
    if e9 > e21 and 55 <= r <= 70:
        direction = "CALL"
    elif e9 < e21 and 30 <= r <= 45:
        direction = "PUT"
    else:
        # Não emite sinal neutro (retorna None) para não poluir feed
        return None

    return {
        "ativo": symbol,
        "preco": round(price, 5),
        "sinal": direction,
        "rsi": round(r, 2),
        "ema9": round(e9, 5),
        "ema21": round(e21, 5),
        "confianca": round(confidence, 2),
        "timestamp": _now_utc().isoformat(),
    }

async def analisar_simbolo(symbol: str) -> Optional[Dict[str, Any]]:
    try:
        df = await fetch_timeseries(symbol, interval="1min", outputsize=180)
        return sinal_from_indicators(symbol, df)
    except Exception as e:
        # Silencioso por símbolo; seguimos pro próximo
        return None

async def melhor_sinal(symbols: List[str], conf_min: float) -> Optional[Dict[str, Any]]:
    """
    Avalia lista de símbolos e retorna o melhor sinal com confiança >= conf_min.
    """
    tasks = [analisar_simbolo(s) for s in symbols]
    results = await asyncio.gather(*tasks)

    # Filtra sinais válidos
    valid = [s for s in results if s and s.get("confianca", 0) >= conf_min]
    if not valid:
        return None

    # Escolhe maior confiança
    best = max(valid, key=lambda x: x.get("confianca", 0.0))
    return best

async def send_telegram_message(text: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            await client.post(url, json=payload)
        except Exception:
            pass

def format_msg(signal: Dict[str, Any]) -> str:
    return (
        "👑 <b>IA do Imperador 4.0</b>\n"
        f"• Ativo: <b>{signal['ativo']}</b>\n"
        f"• Sinal: <b>{signal['sinal']}</b>\n"
        f"• Confiança: <b>{signal['confianca']}%</b>\n"
        f"• Preço: {signal['preco']}\n"
        f"• RSI(14): {signal['rsi']} | EMA9: {signal['ema9']} | EMA21: {signal['ema21']}\n"
        f"• Horário (UTC): {signal['timestamp']}\n"
        "#imperadorvip"
    )

# ---------------------------
# MODELOS
# ---------------------------
class ToggleBody(BaseModel):
    ativo: bool

class AnaliseBody(BaseModel):
    symbol: Optional[str] = None
    symbols: Optional[List[str]] = None
    conf_min: Optional[float] = None

# ---------------------------
# ROTAS
# ---------------------------

@app.get("/")
async def root():
    return {"status": "ok", "service": "ImperadorVIP Signals API", "time": _now_utc().isoformat()}

@app.get("/healthz")
async def healthz():
    return {"ok": True, "time": _now_utc().isoformat()}

@app.get("/signal/live")
async def signal_live():
    """
    O Base44 consome esta rota.
    - Se houver sinal recente (<= 5 min), retorna.
    - Senão, tenta gerar um novo (melhor da lista) com conf >= 90.
    """
    global LAST_SIGNAL, LAST_SIGNAL_AT

    # Se houver cache recente, retorna
    if LAST_SIGNAL and LAST_SIGNAL_AT and (_now_utc() - LAST_SIGNAL_AT) <= timedelta(minutes=5):
        return {"status": "ok", "sinal": LAST_SIGNAL}

    # Gera novo
    best = await melhor_sinal(DEFAULT_SYMBOLS, CONF_MIN_DEFAULT)
    if not best:
        return {"detail": "Nenhum sinal disponível ainda"}

    LAST_SIGNAL = best
    LAST_SIGNAL_AT = _now_utc()
    return {"status": "ok", "sinal": best}

@app.post("/analisar")
async def analisar(body: AnaliseBody = Body(...)):
    """
    Usado pelo botão 'Testar Análise com Dados Reais' no Base44.
    Aceita:
    - symbol="EUR/USD"
    - symbols=["EUR/USD","USD/JPY",...]
    - conf_min=90
    """
    conf_min = float(body.conf_min) if body.conf_min is not None else CONF_MIN_DEFAULT

    if body.symbol:
        sig = await analisar_simbolo(body.symbol)
        if sig and sig.get("confianca", 0) >= conf_min:
            return {"status": "ok", "sinal": sig}
        return {"detail": "Nenhum sinal disponível ainda"}

    symbols = body.symbols if body.symbols else DEFAULT_SYMBOLS
    best = await melhor_sinal(symbols, conf_min)
    if not best:
        return {"detail": "Nenhum sinal disponível ainda"}
    return {"status": "ok", "sinal": best}

@app.get("/bot/status")
async def bot_status():
    return {"bot_status": BOT_ACTIVE}

@app.post("/bot/status")
async def alternar_bot(body: ToggleBody):
    """
    Compatível com o Base44 (envia {ativo:true/false}).
    """
    global BOT_ACTIVE
    BOT_ACTIVE = bool(body.ativo)
    return {"bot_status": BOT_ACTIVE, "msg": "Bot atualizado com sucesso"}

# ---------------------------
# LOOP AUTOMÁTICO (5 min)
# ---------------------------

async def bot_loop():
    global LAST_SIGNAL, LAST_SIGNAL_AT

    while not _stop_event.is_set():
        try:
            if BOT_ACTIVE:
                best = await melhor_sinal(DEFAULT_SYMBOLS, CONF_MIN_DEFAULT)
                if best:
                    LAST_SIGNAL = best
                    LAST_SIGNAL_AT = _now_utc()
                    await send_telegram_message(format_msg(best))
        except Exception as e:
            # Evita derrubar o serviço por erro intermitente da API
            pass

        # Espera 5 minutos (ou até sinal de parada)
        try:
            await asyncio.wait_for(_stop_event.wait(), timeout=300)  # 5 * 60
        except asyncio.TimeoutError:
            continue

@app.on_event("startup")
async def on_startup():
    global _loop_task, _stop_event
    _stop_event = asyncio.Event()
    _loop_task = asyncio.create_task(bot_loop())

@app.on_event("shutdown")
async def on_shutdown():
    global _loop_task
    _stop_event.set()
    if _loop_task:
        try:
            await asyncio.wait_for(_loop_task, timeout=5)
        except Exception:
            pass

# ---------------------------
# Execução local
# ---------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
