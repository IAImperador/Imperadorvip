# -*- coding: utf-8 -*-
from fastapi import FastAPI, Body
from pydantic import BaseModel
from typing import Dict, List, Optional
import threading, time, json, os
import requests
import websocket  # websocket-client
import pandas as pd
import numpy as np

# ====== CONFIGURAÇÕES GERAIS ======
APP_TITLE = "ImperadorVIP - Global Signal Engine (Public Feeds)"
app = FastAPI(title=APP_TITLE)

# --- Modo de operação ---
AUTO_MODE = False  # alterna via /mode/{state}

# --- Telegram (preencha para ativar) ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "COLOQUE_SEU_TOKEN_AQUI")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID",   "COLOQUE_SEU_CHATID_AQUI")

# --- Base44 (opcional) ---
BASE44_SIGNALS_URL = os.getenv("BASE44_SIGNALS_URL", "")  # ex: https://suaapi.base44/sinais

# --- Thresholds de sinal ---
MIN_CONFLUENCES = int(os.getenv("MIN_CONFLUENCES", "3"))
MIN_SCORE       = float(os.getenv("MIN_SCORE", "0.6"))

# --- Feeds públicos ativados ---
ENABLE_DERIV   = True   # público: wss deriv
ENABLE_QUOTEX  = False  # NÃO público (stub desativado)
ENABLE_IQ      = False  # NÃO público (stub desativado)

# --- Universo de ativos (Deriv) ---
# Se quiser tudo, mantenha vazio e o sistema assina um subconjunto popular.
DERIV_ASSETS_WHITELIST: List[str] = []   # ex: ["frxEURUSD", "frxGBPUSD", "cryBTCUSD"]

# ====== ESTADOS EM MEMÓRIA ======
latest_prices: Dict[str, float] = {}             # {symbol: price}
last_update_ts: Dict[str, float] = {}            # {symbol: ts}
candles: Dict[str, List[Dict]] = {}              # {symbol: [ {t,o,h,l,c} ]}
signals_feed: List[Dict] = []                    # sinalizações geradas
status_flags = {
    "deriv_connected": False,
    "quotex_connected": False,
    "iq_connected": False
}

CANDLE_SECONDS = 60  # 1m candles
MAX_CANDLES    = 200

# ====== UTIL ======
def now_ts() -> float:
    return time.time()

def send_telegram(text: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID or "COLOQUE" in TELEGRAM_BOT_TOKEN:
        print("[TELEGRAM] Token/ChatID não configurado. Ignorando envio.")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"[TELEGRAM] erro ao enviar: {e}")

def post_base44(payload: Dict) -> None:
    if not BASE44_SIGNALS_URL:
        return
    try:
        requests.post(BASE44_SIGNALS_URL, json=payload, timeout=10)
    except Exception as e:
        print(f"[BASE44] erro ao postar sinal: {e}")

def ensure_symbol_books(symbol: str):
    if symbol not in candles:
        candles[symbol] = []

# ====== CONSTRUÇÃO DE CANDLE A PARTIR DE TICKS ======
def apply_tick(symbol: str, price: float, ts: Optional[float] = None):
    t = ts or now_ts()
    latest_prices[symbol] = price
    last_update_ts[symbol] = t
    ensure_symbol_books(symbol)

    # bucket de 1 minuto
    bucket = int(t // CANDLE_SECONDS) * CANDLE_SECONDS

    book = candles[symbol]
    if not book or book[-1]["t"] != bucket:
        # inicia nova vela
        book.append({"t": bucket, "o": price, "h": price, "l": price, "c": price})
        if len(book) > MAX_CANDLES:
            del book[:-MAX_CANDLES]
    else:
        v = book[-1]
        v["h"] = max(v["h"], price)
        v["l"] = min(v["l"], price)
        v["c"] = price

# ====== INDICADORES & CONFLUÊNCIAS ======
def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    # df: columns = [t,o,h,l,c]
    out = df.copy()
    # EMA9 / EMA21
    out["ema9"]  = out["c"].ewm(span=9, adjust=False).mean()
    out["ema21"] = out["c"].ewm(span=21, adjust=False).mean()
    # RSI14
    delta = out["c"].diff()
    gain  = (delta.clip(lower=0)).ewm(alpha=1/14, adjust=False).mean()
    loss  = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs    = gain / (loss.replace(0, np.nan))
    out["rsi14"] = 100 - (100 / (1 + rs))
    out["rsi14"] = out["rsi14"].fillna(method="bfill").fillna(50)
    return out

def detect_engulfing(df: pd.DataFrame) -> Optional[str]:
    # very simple engulfing on last two candles
    if len(df) < 2:
        return None
    a = df.iloc[-2]
    b = df.iloc[-1]
    # bullish engulfing
    if (a["c"] < a["o"]) and (b["c"] > b["o"]) and (b["c"] >= a["o"]) and (b["o"] <= a["c"]):
        return "bullish"
    # bearish engulfing
    if (a["c"] > a["o"]) and (b["c"] < b["o"]) and (b["c"] <= a["o"]) and (b["o"] >= a["c"]):
        return "bearish"
    return None

def build_signal_from_confluences(symbol: str) -> Optional[Dict]:
    book = candles.get(symbol, [])
    if len(book) < 25:
        return None
    df = pd.DataFrame(book)[["t","o","h","l","c"]]
    ind = compute_indicators(df)
    last = ind.iloc[-1]

    confluences = []
    # Tendência por EMAs
    if last["ema9"] > last["ema21"]:
        confluences.append("trend_up")
    elif last["ema9"] < last["ema21"]:
        confluences.append("trend_down")

    # RSI zonas
    if last["rsi14"] < 30:
        confluences.append("rsi_oversold")
    elif last["rsi14"] > 70:
        confluences.append("rsi_overbought")

    # Engulfing
    engulf = detect_engulfing(ind)
    if engulf == "bullish":
        confluences.append("bullish_engulfing")
    elif engulf == "bearish":
        confluences.append("bearish_engulfing")

    # direcionalidade simples
    direction = None
    if "trend_up" in confluences or "bullish_engulfing" in confluences:
        direction = "CALL"
    if "trend_down" in confluences or "bearish_engulfing" in confluences:
        # se houver sinais opostos, desempata por EMA
        direction = "PUT" if last["ema9"] <= last["ema21"] else direction

    score = min(1.0, (len(confluences) / 5.0) + (0.1 if direction else 0.0))
    if len(confluences) >= MIN_CONFLUENCES and score >= MIN_SCORE and direction:
        sig = {
            "symbol": symbol,
            "direction": direction,
            "score": round(score, 3),
            "confluences": confluences,
            "ts": int(now_ts()),
            "price": float(latest_prices.get(symbol, float('nan')))
        }
        return sig
    return None

def maybe_emit_signal(symbol: str):
    sig = build_signal_from_confluences(symbol)
    if not sig:
        return
    # guarda no feed
    signals_feed.append(sig)
    if len(signals_feed) > 200:
        del signals_feed[:-200]

    # mensagem
    msg = (
        f"📡 <b>Signal</b>\n"
        f"Ativo: <b>{sig['symbol']}</b>\n"
        f"Direção: <b>{sig['direction']}</b>\n"
        f"Score: <b>{sig['score']}</b>\n"
        f"Confluências: {', '.join(sig['confluences'])}\n"
        f"Preço: {sig['price']}"
    )

    # Auto vs Manual
    if AUTO_MODE:
        send_telegram(msg)
        post_base44(sig)
        print("[AUTO] Sinal enviado para Telegram/Base44.")
    else:
        print("[MANUAL] Sinal disponível no feed (use /signals).")

# ====== ADAPTER: DERIV (PÚBLICO) ======
def deriv_on_message(ws, message):
    try:
        data = json.loads(message)
        # active_symbols result
        if data.get("active_symbols"):
            # filtra símbolos (forex/crypto/índices)
            syms = []
            for s in data["active_symbols"]:
                if DERIV_ASSETS_WHITELIST and s["symbol"] not in DERIV_ASSETS_WHITELIST:
                    continue
                if s.get("market") in ("forex", "cryptocurrency", "synthetic_index", "indices"):
                    syms.append(s["symbol"])
            # limita para não sobrecarregar
            syms = syms[:40] if len(syms) > 40 else syms
            for sym in syms:
                ws.send(json.dumps({"ticks": sym, "subscribe": 1}))
            print(f"[DERIV] Subscribed to {len(syms)} symbols.")
            return

        # ticks
        if data.get("tick"):
            sym = data["tick"]["symbol"]
            price = float(data["tick"]["quote"])
            ts = data["tick"]["epoch"]
            # converte símbolo deriv -> padrão (mantemos original)
            apply_tick(sym, price, ts)
            # tenta gerar sinal
            maybe_emit_signal(sym)
    except Exception as e:
        print(f"[DERIV on_message] {e}")

def deriv_on_open(ws):
    status_flags["deriv_connected"] = True
    print("[DERIV] Connected.")
    # solicita lista de ativos
    ws.send(json.dumps({"active_symbols": "brief", "product_type": "basic"}))

def deriv_on_error(ws, error):
    print(f"[DERIV Error] {error}")

def deriv_on_close(ws, code, reason):
    status_flags["deriv_connected"] = False
    print(f"[DERIV] Closed ({code}). Reconnecting in 5s...")
    time.sleep(5)
    start_deriv_ws()

def start_deriv_ws():
    try:
        # app_id público de exemplo (uso em leitura). Substitua pelo seu se tiver.
        url = "wss://ws.derivws.com/websockets/v3?app_id=1089"
        ws = websocket.WebSocketApp(
            url,
            on_open=deriv_on_open,
            on_message=deriv_on_message,
            on_error=deriv_on_error,
            on_close=deriv_on_close
        )
        ws.run_forever(reconnect=5)
    except Exception as e:
        print(f"[DERIV start] {e}")

# ====== ADAPTERS STUBS (DESLIGADOS POR PADRÃO) ======
def start_quotex_ws_stub():
    # Stub seguro: não usa endpoints privados
    status_flags["quotex_connected"] = False
    print("[QUOTEX] Stub público desativado (sem API pública).")

def start_iq_ws_stub():
    status_flags["iq_connected"] = False
    print("[IQOPTION] Stub público desativado (sem API pública).")

# ====== STARTUP ======
@app.on_event("startup")
async def startup_event():
    print("🚀 Iniciando feeds...")
    if ENABLE_DERIV:
        threading.Thread(target=start_deriv_ws, daemon=True).start()
    if ENABLE_QUOTEX:
        threading.Thread(target=start_quotex_ws_stub, daemon=True).start()
    if ENABLE_IQ:
        threading.Thread(target=start_iq_ws_stub, daemon=True).start()

# ====== ROTAS HTTP ======
@app.get("/")
def root():
    return {
        "app": APP_TITLE,
        "auto_mode": AUTO_MODE,
        "feeds": status_flags,
        "symbols_tracked": list(candles.keys())
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/status")
def status():
    return {
        "feeds": status_flags,
        "prices_count": len(latest_prices),
        "signals_count": len(signals_feed)
    }

@app.post("/mode/{state}")
def set_mode(state: str):
    global AUTO_MODE
    AUTO_MODE = (state.lower() == "auto")
    return {"mode": "auto" if AUTO_MODE else "manual"}

@app.get("/price/{symbol}")
def get_price(symbol: str):
    if symbol in latest_prices:
        return {"symbol": symbol, "price": latest_prices[symbol], "ts": last_update_ts.get(symbol)}
    return {"error": "symbol not tracked"}

@app.get("/candles/{symbol}")
def get_candles(symbol: str):
    if symbol in candles:
        return {"symbol": symbol, "candles": candles[symbol][-100:]}
    return {"error": "symbol not tracked"}

@app.get("/signals")
def list_signals():
    return {"signals": signals_feed[-50:]}

class ManualSignal(BaseModel):
    symbol: str
    direction: str
    note: Optional[str] = None

@app.post("/signal/manual")
def manual_signal(sig: ManualSignal):
    payload = {
        "symbol": sig.symbol,
        "direction": sig.direction.upper(),
        "score": 1.0,
        "confluences": ["manual"],
        "ts": int(now_ts()),
        "price": float(latest_prices.get(sig.symbol, float("nan"))),
        "note": sig.note or ""
    }
    signals_feed.append(payload)
    if AUTO_MODE:
        send_telegram(f"📡 <b>Signal MANUAL</b>\nAtivo: <b>{payload['symbol']}</b>\nDireção: <b>{payload['direction']}</b>\nPreço: {payload['price']}\nNota: {payload['note']}")
        post_base44(payload)
    return {"ok": True, "signal": payload}

# Execução local (Railway usa uvicorn externo)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
