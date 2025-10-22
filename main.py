# ======================================================
# 🚀 IMPERADORVIP - IA DE CONFLUÊNCIA MULTI-CORRETORAS (REAL-TIME)
# ======================================================

from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, List, Any
import os
import time
import math
import requests
import pandas as pd
import numpy as np
import ta

# ======================================================
# ⚙️ CONFIGURAÇÃO DO SERVIDOR E CORS
# ======================================================

app = FastAPI(title="ImperadorVIP IA", version="3.2")

ALLOWED_ORIGINS = [
    "https://imperadorvip.base44.app",
    "https://app.base44.io",
    "https://studio.base44.io",
    "https://base44.app",
    "https://imperadorvip-production-e55d.up.railway.app",
    "*"  # mantém por compatibilidade/ambiente de testes
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# 🔧 VARIÁVEIS DE AMBIENTE
# ======================================================

APP_NAME = os.getenv("APP_NAME", "ImperadorVIP")
PORT = int(os.getenv("PORT", "8080"))
API_KEY = os.getenv("API_KEY", "imperadorvip-secure-key-2025")
TWELVEDATA_KEY = os.getenv("TWELVEDATA_KEY")  # deve existir
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

if not TWELVEDATA_KEY or len(TWELVEDATA_KEY) < 10:
    # falha cedo: deixa claro nos logs do Railway
    print("❌ TWELVEDATA_KEY ausente ou inválida. Configure em Railway → Variables.")
else:
    print(f"✅ TWELVEDATA_KEY carregada: {TWELVEDATA_KEY[:6]}********")

print(f"✅ API_KEY configurada: {('sim' if API_KEY else 'não')}")
if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
    print("✅ Telegram pronto para envio (opcional).")
else:
    print("ℹ️ Telegram desativado (defina TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID para ativar).")

# Flag de envio automático (em memória do processo)
BOT_AUTO = False

# ======================================================
# 📚 CATÁLOGO DE ATIVOS SUPORTADOS POR CORRETORA
# (curado para garantir que não sugerimos ativo inexistente)
# ======================================================

BROKER_ASSETS: Dict[str, Dict[str, List[str]]] = {
    # Observação: mapeie ativos que realmente aparecem na corretora.
    # Você pode expandir conforme necessidade.
    "Quotex": {
        "binary": ["EUR/USD", "GBP/USD", "USD/JPY", "EUR/JPY", "AUD/USD", "USD/CHF", "EUR/GBP"],
        "crypto": ["BTC/USD", "ETH/USD", "LTC/USD"],
        "otc": ["EUR/USD", "GBP/USD"],  # pares OTC comuns
    },
    "IQ Option": {
        "binary": ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CAD", "AUD/USD", "NZD/USD", "USD/CHF", "EUR/GBP"],
        "digital": ["EUR/USD", "GBP/USD", "USD/JPY"],
        "crypto": ["BTC/USD", "ETH/USD", "XRP/USD"],
        "otc": ["EUR/USD", "USD/JPY"],
    },
    "Deriv": {
        "binary": ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CHF", "EUR/GBP"],
        "synthetic": ["R_10", "R_25", "R_50", "R_75", "R_100"],  # índices sintéticos (ex.: Deriv)
        "otc": ["EUR/USD"],
    },
    "Binomo": {
        "binary": ["EUR/USD", "GBP/USD", "USD/JPY", "EUR/JPY", "AUD/USD"],
        "crypto": ["BTC/USD", "ETH/USD"],
        "otc": ["EUR/USD"],
    },
    "Pocket Option": {
        "binary": ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "EUR/GBP", "AUD/USD"],
        "crypto": ["BTC/USD", "ETH/USD"],
        "otc": ["EUR/USD", "GBP/USD"],
    },
    "Olymp Trade": {
        "binary": ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "EUR/GBP", "AUD/USD"],
        "crypto": ["BTC/USD", "ETH/USD"],
        "otc": ["EUR/USD"],
    },
    "Avalon": {
        "binary": ["EUR/USD", "GBP/USD", "USD/JPY"],
        "crypto": ["BTC/USD"],
        "otc": ["EUR/USD"],
    },
    "BulleX": {
        "binary": ["EUR/USD", "GBP/USD", "USD/JPY"],
        "crypto": ["BTC/USD", "ETH/USD"],
    },
    "Casa Trader": {
        "binary": ["EUR/USD", "GBP/USD"],
        "crypto": ["BTC/USD"],
    },
    "NexBroker": {
        "binary": ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"],
        "crypto": ["BTC/USD"],
    },
    "Polaryum": {   # ortografia corrigida
        "binary": ["EUR/USD", "GBP/USD"],
        "crypto": ["BTC/USD"],
    },
    "Broker10": {   # ortografia corrigida
        "binary": ["EUR/USD", "USD/JPY"],
        "crypto": ["BTC/USD"],
    },
}

BROKERS = list(BROKER_ASSETS.keys())

# ======================================================
# 🔐 AUTENTICAÇÃO SIMPLES POR API KEY
# ======================================================

def require_api_key(x_api_key: Optional[str] = Header(None)):
    if not API_KEY:
        # Sem API_KEY definida no ambiente → não exige
        return True
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="API key inválida.")
    return True

# ======================================================
# 🔗 HELPERS: MAPEAMENTO DE SÍMBOLO & DADOS
# ======================================================

def _normalize_symbol_for_twelvedata(symbol: str) -> str:
    """Converte 'EUR/USD' -> 'EURUSD' e deixa outros como estão."""
    s = symbol.replace(" ", "").upper()
    if "/" in s:
        s = s.replace("/", "")
    return s

def _is_supported_asset(broker: str, asset: str) -> bool:
    assets = BROKER_ASSETS.get(broker, {})
    for _class, items in assets.items():
        if asset in items:
            return True
    return False

def _twelvedata_get_timeseries(symbol: str, interval: str = "1min", outputsize: int = 200, timeout: int = 8, retries: int = 2) -> pd.DataFrame:
    """
    Busca candles reais na TwelveData.
    Lança HTTPException com mensagens claras em caso de erro.
    """
    if not TWELVEDATA_KEY or len(TWELVEDATA_KEY) < 10:
        raise HTTPException(status_code=500, detail="TWELVEDATA_KEY não configurada ou inválida no servidor.")

    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "apikey": TWELVEDATA_KEY,
        "outputsize": outputsize,
        "order": "ASC",  # mais antigos → mais novos
        "format": "JSON"
    }

    last_exc = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            if resp.status_code != 200:
                last_exc = HTTPException(status_code=resp.status_code, detail=f"TwelveData HTTP {resp.status_code}: {resp.text[:200]}")
                time.sleep(0.8)
                continue
            data = resp.json()
            if "values" not in data:
                # Mensagem clara para debug
                detail = data.get("message") or data
                raise HTTPException(status_code=400, detail=f"Erro ao buscar dados (TwelveData): {detail}")
            df = pd.DataFrame(data["values"])
            # Normaliza tipos
            for col in ("open", "high", "low", "close"):
                df[col] = df[col].astype(float)
            df["datetime"] = pd.to_datetime(df["datetime"])
            df = df.sort_values("datetime").reset_index(drop=True)
            return df
        except requests.Timeout as e:
            last_exc = HTTPException(status_code=504, detail="Timeout ao consultar dados na TwelveData.")
        except Exception as e:
            last_exc = HTTPException(status_code=500, detail=f"Falha ao consultar TwelveData: {str(e)}")
        time.sleep(0.8)

    raise last_exc or HTTPException(status_code=500, detail="Falha desconhecida ao consultar TwelveData.")

# ======================================================
# 🧠 ANÁLISE: INDICADORES + PADRÕES + CONFLUÊNCIA
# ======================================================

def _compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    close = df["close"]
    high = df["high"]
    low = df["low"]

    # Indicadores clássicos
    df["ema_9"] = ta.trend.EMAIndicator(close, window=9).ema_indicator()
    df["ema_21"] = ta.trend.EMAIndicator(close, window=21).ema_indicator()
    macd = ta.trend.MACD(close)
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    bb = ta.volatility.BollingerBands(close)
    df["bb_h"] = bb.bollinger_hband()
    df["bb_l"] = bb.bollinger_lband()
    df["rsi"] = ta.momentum.RSIIndicator(close, window=14).rsi()
    stoch = ta.momentum.StochasticOscillator(high, low, close)
    df["stoch_k"] = stoch.stoch()
    df["stoch_d"] = stoch.stoch_signal()
    df["atr"] = ta.volatility.AverageTrueRange(high, low, close, window=14).average_true_range()

    # Direção/força de tendência (simples)
    df["ema_trend"] = np.where(df["ema_9"] > df["ema_21"], 1, -1)
    df["macd_trend"] = np.where(df["macd"] > df["macd_signal"], 1, -1)

    return df

def _detect_candle_patterns(df: pd.DataFrame) -> Dict[str, bool]:
    """Padrões básicos de candle no último candle."""
    if len(df) < 3:
        return {}
    last = df.iloc[-1]
    prev = df.iloc[-2]
    prev2 = df.iloc[-3]

    def body(c):
        return abs(c["close"] - c["open"])

    patterns = {}

    # Engolfo de Alta/Baixa (bem simplificado)
    patterns["bullish_engulfing"] = (prev["close"] < prev["open"]) and (last["close"] > last["open"]) and (last["close"] >= prev["open"]) and (last["open"] <= prev["close"])
    patterns["bearish_engulfing"] = (prev["close"] > prev["open"]) and (last["close"] < last["open"]) and (last["open"] >= prev["close"]) and (last["close"] <= prev["open"])

    # Martelo / Martelo Invertido (simplificado)
    last_range = last["high"] - last["low"]
    upper_shadow = last["high"] - max(last["close"], last["open"])
    lower_shadow = min(last["close"], last["open"]) - last["low"]
    patterns["hammer"] = (lower_shadow > body(last) * 1.5) and (upper_shadow < body(last))
    patterns["inverted_hammer"] = (upper_shadow > body(last) * 1.5) and (lower_shadow < body(last))

    # Doji (corpo pequeno)
    patterns["doji"] = body(last) <= (last_range * 0.1)

    # Inside Bar
    patterns["inside_bar"] = (last["high"] <= prev["high"]) and (last["low"] >= prev["low"])

    # Three Soldiers/Crows (bem simplificado)
    patterns["three_white_soldiers"] = (prev2["close"] > prev2["open"]) and (prev["close"] > prev["open"]) and (last["close"] > last["open"])
    patterns["three_black_crows"] = (prev2["close"] < prev2["open"]) and (prev["close"] < prev["open"]) and (last["close"] < last["open"])

    return patterns

def _support_resistance_confluence(df: pd.DataFrame, lookback: int = 80) -> Dict[str, Any]:
    """Detecta zonas simples de S/R e posição do preço atual nelas."""
    if len(df) < max(lookback, 20):
        return {"sr": [], "in_zone": False}

    window = df.tail(lookback)
    highs = window["high"].values
    lows = window["low"].values
    # níveis simples: máximas/mínimas locais
    sr_levels = [np.max(highs), np.min(lows)]
    price = df.iloc[-1]["close"]

    # Considera "em zona" se dentro de 0.15*ATR da S ou R
    atr = window["atr"].iloc[-1] if "atr" in window.columns else (window["high"] - window["low"]).mean()
    tol = max(atr * 0.15, price * 0.0005)

    in_zone = any(abs(price - level) <= tol for level in sr_levels)
    return {"sr": sr_levels, "in_zone": in_zone, "tol": tol}

def _channel_trend_confluence(df: pd.DataFrame, lookback: int = 80) -> Dict[str, Any]:
    """Checagem simples de canal/tendência via regressão linear."""
    if len(df) < lookback:
        return {"trend": "flat", "slope": 0.0}
    window = df.tail(lookback)
    y = window["close"].values
    x = np.arange(len(y))
    # regressão linear simples
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    num = np.sum((x - x_mean) * (y - y_mean))
    den = np.sum((x - x_mean) ** 2) + 1e-9
    slope = num / den
    trend = "up" if slope > 0 else "down" if slope < 0 else "flat"
    return {"trend": trend, "slope": float(slope)}

def _first_record_confluence(df: pd.DataFrame) -> bool:
    """'Primeiro registro' (candle de abertura da sessão/OTC) simplificado: se estamos nos primeiros 5 candles do dia UTC."""
    if "datetime" not in df.columns:
        return False
    last_dt = df.iloc[-1]["datetime"]
    # aproximação: primeiros 5 minutos/hora conforme intervalo curto
    # aqui só marcamos True se minuto < 5
    return last_dt.minute < 5

def _price_limit_confluence(df: pd.DataFrame) -> bool:
    """Limite de preço: preço atual próximo de BBands extremas."""
    last = df.iloc[-1]
    if pd.isna(last.get("bb_h", np.nan)) or pd.isna(last.get("bb_l", np.nan)):
        return False
    return (last["close"] >= last["bb_h"]) or (last["close"] <= last["bb_l"])

def _decision_from_confluences(df: pd.DataFrame) -> Dict[str, Any]:
    """Gera sinal CALL/PUT/WAIT e confiança baseada em confluências."""
    last = df.iloc[-1]

    # Confluências base
    confluences = []

    # Tendência por EMAs
    ema_bull = last["ema_9"] > last["ema_21"]
    ema_bear = last["ema_9"] < last["ema_21"]
    if ema_bull: confluences.append("ema_up")
    if ema_bear: confluences.append("ema_down")

    # MACD
    macd_bull = last["macd"] > last["macd_signal"]
    macd_bear = last["macd"] < last["macd_signal"]
    if macd_bull: confluences.append("macd_up")
    if macd_bear: confluences.append("macd_down")

    # RSI zonas
    rsi = last["rsi"]
    rsi_overbought = rsi >= 70
    rsi_oversold = rsi <= 30
    if rsi_oversold: confluences.append("rsi_oversold")
    if rsi_overbought: confluences.append("rsi_overbought")

    # Bandas de Bollinger (limite de preço)
    near_limit = _price_limit_confluence(df)
    if near_limit: confluences.append("price_limit")

    # Padrões de candle
    pats = _detect_candle_patterns(df)
    for k, v in pats.items():
        if v: confluences.append(k)

    # Suporte/Resistência
    sr = _support_resistance_confluence(df)
    if sr.get("in_zone"): confluences.append("sr_zone")

    # Canal / LTA / LTB
    ch = _channel_trend_confluence(df)
    if ch["trend"] == "up": confluences.append("lta")
    elif ch["trend"] == "down": confluences.append("ltb")

    # Primeiro registro (só pontua, não decide sozinho)
    if _first_record_confluence(df): confluences.append("first_record")

    # Decisão
    bullish_votes = int(ema_bull) + int(macd_bull) + int(rsi_oversold) + int(pats.get("bullish_engulfing", False)) + int(pats.get("hammer", False))
    bearish_votes = int(ema_bear) + int(macd_bear) + int(rsi_overbought) + int(pats.get("bearish_engulfing", False)) + int(pats.get("inverted_hammer", False))

    # Ajuste por SR e limite de preço: se em resistência e esticado → favorece PUT; se em suporte e esticado → CALL
    # (simplificação: se price_limit + SR zone e tendência para cima → cuidado; tendência para baixo → cuidado)
    if sr.get("in_zone", False) and near_limit:
        # adiciona voto contrário à tendência para prever retração
        if ema_bull or macd_bull:
            bearish_votes += 1
        if ema_bear or macd_bear:
            bullish_votes += 1

    if bullish_votes > bearish_votes and bullish_votes >= 2:
        signal = "CALL"
    elif bearish_votes > bullish_votes and bearish_votes >= 2:
        signal = "PUT"
    else:
        signal = "WAIT"

    # Confiança: baseado na quantidade de confluências únicas
    unique_conf = len(set(confluences))
    # escore base 60 + 5 por confluência, com bônus por concordância de EMA+MACD
    base_conf = 60 + unique_conf * 5
    if (ema_bull and macd_bull) or (ema_bear and macd_bear):
        base_conf += 10
    base_conf = max(50, min(98, base_conf))  # clamp 50–98

    return {
        "signal": signal,
        "confidence": round(float(base_conf), 2),
        "confluences": sorted(list(set(confluences))),
        "trend": ch.get("trend", "flat"),
        "sr": sr.get("sr", []),
    }

# ======================================================
# 🔔 TELEGRAM (OPCIONAL)
# ======================================================

def send_telegram_message(text: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
        r = requests.post(url, json=payload, timeout=8)
        return r.status_code == 200
    except Exception:
        return False

# ======================================================
# 🌐 ROTAS PÚBLICAS BÁSICAS
# ======================================================

@app.get("/")
def root():
    return {
        "status": "online",
        "app": APP_NAME,
        "brokers_enabled": BROKERS,
        "message": f"IA {APP_NAME} conectada com sucesso à Base44 e Railway."
    }

@app.get("/health")
def health():
    return {"status": "healthy", "brokers_count": len(BROKERS), "bot_auto": BOT_AUTO}

@app.get("/brokers")
def list_brokers():
    return {"brokers": BROKERS}

@app.get("/assets")
def list_assets(broker: str):
    if broker not in BROKER_ASSETS:
        raise HTTPException(status_code=400, detail=f"Corretora '{broker}' não suportada.")
    return {"broker": broker, "assets": BROKER_ASSETS[broker]}

# ======================================================
# 🧠 ENDPOINT DE ANÁLISE (PROTEGIDO POR API KEY)
# ======================================================

@app.post("/analyze")
async def analyze(request: Request, _: bool = Depends(require_api_key)):
    """
    Body esperado:
    {
      "broker": "Quotex",
      "asset": "EUR/USD",
      "interval": "1min" | "5min" | "15min",
      "market": "OTC" | "CRYPTO" | ...
    }
    """
    body = await request.json()

    broker = body.get("broker", "Quotex")
    asset = body.get("asset", "EUR/USD")
    interval = body.get("interval", "1min")
    market = body.get("market", "OTC")

    if broker not in BROKER_ASSETS:
        raise HTTPException(status_code=400, detail=f"Corretora '{broker}' não suportada.")

    if not _is_supported_asset(broker, asset):
        raise HTTPException(status_code=400, detail=f"O ativo '{asset}' não pertence à corretora '{broker}'. Use /assets?broker={broker} para listar os suportados.")

    # Deriv sintéticos não existem na TwelveData → recusa (ou implementar fonte própria)
    if broker == "Deriv" and asset in BROKER_ASSETS["Deriv"].get("synthetic", []):
        raise HTTPException(status_code=422, detail="Ativos sintéticos da Deriv não estão disponíveis via TwelveData.")

    # Normaliza símbolo para TwelveData
    td_symbol = _normalize_symbol_for_twelvedata(asset)

    # Busca dados reais
    df = _twelvedata_get_timeseries(td_symbol, interval=interval, outputsize=200)

    # Garante colunas open/high/low/close e datetime
    needed_cols = {"open", "high", "low", "close", "datetime"}
    if not needed_cols.issubset(df.columns):
        raise HTTPException(status_code=500, detail=f"Dados incompletos da TwelveData. Campos faltando: {sorted(list(needed_cols - set(df.columns)))}")

    # Calcula indicadores & confluências
    df = _compute_indicators(df)
    decision = _decision_from_confluences(df)
    last = df.iloc[-1]

    # Payload final
    result = {
        "broker": broker,
        "asset": asset,
        "interval": interval,
        "market": market,
        "timestamp": str(last["datetime"]),
        "last_price": round(float(last["close"]), 6),
        "signal": decision["signal"],
        "confidence": decision["confidence"],
        "trend": decision["trend"],
        "confluences": decision["confluences"],
        "indicators": {
            "rsi": round(float(last["rsi"]), 2),
            "ema_9": round(float(last["ema_9"]), 6),
            "ema_21": round(float(last["ema_21"]), 6),
            "macd": round(float(last["macd"]), 6),
            "macd_signal": round(float(last["macd_signal"]), 6),
            "bb_h": round(float(last["bb_h"]), 6) if not math.isnan(last["bb_h"]) else None,
            "bb_l": round(float(last["bb_l"]), 6) if not math.isnan(last["bb_l"]) else None,
            "stoch_k": round(float(last["stoch_k"]), 2) if not math.isnan(last["stoch_k"]) else None,
            "stoch_d": round(float(last["stoch_d"]), 2) if not math.isnan(last["stoch_d"]) else None,
            "atr": round(float(last["atr"]), 6) if not math.isnan(last["atr"]) else None,
        }
    }

    # Envio automático para Telegram (se habilitado)
    if BOT_AUTO and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID and result["signal"] in ("CALL", "PUT"):
        msg = (
            f"📣 <b>Sinal {APP_NAME}</b>\n"
            f"Corretora: <b>{broker}</b>\n"
            f"Ativo: <b>{asset}</b>\n"
            f"Intervalo: <b>{interval}</b>\n"
            f"Sinal: <b>{result['signal']}</b>\n"
            f"Confiança: <b>{result['confidence']}%</b>\n"
            f"Preço: <b>{result['last_price']}</b>\n"
            f"Confluências: <i>{', '.join(result['confluences'])}</i>\n"
            f"⏱️ {result['timestamp']}"
        )
        send_telegram_message(msg)

    return result

# ======================================================
# 🕹️ CONTROLES DO BOT TELEGRAM (PÚBLICO, MAS ÚTEIS)
# ======================================================

@app.post("/bot/enable")
def bot_enable(_: bool = Depends(require_api_key)):
    global BOT_AUTO
    BOT_AUTO = True
    return {"ok": True, "bot_auto": BOT_AUTO}

@app.post("/bot/disable")
def bot_disable(_: bool = Depends(require_api_key)):
    global BOT_AUTO
    BOT_AUTO = False
    return {"ok": True, "bot_auto": BOT_AUTO}

# ======================================================
# 🧩 EXECUÇÃO LOCAL (debug)
# ======================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
