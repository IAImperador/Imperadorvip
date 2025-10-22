# ======================================================
# 🚀 IMPERADORVIP - IA GLOBAL MULTI-CORRETORAS (v4.0)
# ======================================================

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import os, requests, pandas as pd, numpy as np, ta, asyncio, json

# ======================================================
# ⚙️ CONFIGURAÇÃO DO SERVIDOR E CORS
# ======================================================

app = FastAPI(title="ImperadorVIP IA", version="4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todas as origens
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
TWELVEDATA_KEY = os.getenv("TWELVEDATA_KEY", "demo")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "@IAdoimperador")

# ======================================================
# 💹 CORRETORAS E ATIVOS SUPORTADOS
# ======================================================

BROKERS = {
    "Deriv": ["EUR/USD", "USD/JPY", "GBP/USD", "AUD/USD", "USD/CAD"],
    "Quotex": ["EUR/USD", "USD/JPY", "GBP/USD", "EUR/JPY", "USD/CHF"],
    "IQ Option": ["EUR/USD", "USD/JPY", "GBP/USD", "AUD/CAD", "USD/BRL"],
    "Binomo": ["EUR/USD", "EUR/JPY", "USD/JPY", "GBP/USD", "AUD/USD"],
    "Pocket Option": ["EUR/USD", "USD/CAD", "GBP/USD", "AUD/JPY"],
    "Olymp Trade": ["EUR/USD", "USD/JPY", "GBP/USD", "USD/CHF"],
    "Avalon": ["EUR/USD", "GBP/USD", "AUD/USD", "USD/JPY"],
    "BulleX": ["EUR/USD", "USD/JPY", "GBP/JPY", "AUD/USD"],
    "Casa Trader": ["EUR/USD", "USD/JPY", "USD/BRL", "GBP/USD"],
    "NexBroker": ["EUR/USD", "USD/JPY", "USD/CHF", "GBP/JPY"],
    "Polaryum": ["EUR/USD", "USD/JPY", "BTC/USD", "ETH/USD"],
    "Broker10": ["EUR/USD", "USD/JPY", "GBP/USD", "AUD/USD"],
}

# ======================================================
# 🌐 ROTAS PRINCIPAIS
# ======================================================

@app.get("/")
def root():
    return {
        "status": "online",
        "app": APP_NAME,
        "brokers_enabled": list(BROKERS.keys()),
        "message": f"IA {APP_NAME} conectada com sucesso à Base44 e Railway."
    }

@app.get("/health")
def health():
    return {"status": "healthy", "brokers_count": len(BROKERS)}

# ======================================================
# 🧠 ENDPOINT /analyze (Leitura de gráfico real + confluências)
# ======================================================

@app.post("/analyze")
async def analyze(request: Request):
    try:
        body = await request.json()
        broker = body.get("broker", "Quotex")
        symbol = body.get("symbol", "EUR/USD").replace("/", "")
        interval = body.get("interval", "1min")

        if broker not in BROKERS:
            raise HTTPException(status_code=400, detail="Corretora não suportada.")
        if body.get("symbol") not in BROKERS[broker]:
            raise HTTPException(status_code=400, detail="Ativo indisponível nesta corretora.")

        # === BUSCA DADOS REAIS ===
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&apikey={TWELVEDATA_KEY}&outputsize=100"
        r = requests.get(url, timeout=10)
        data = r.json()

        if "values" not in data:
            raise HTTPException(status_code=400, detail="Erro ao buscar dados do gráfico.")

        df = pd.DataFrame(data["values"]).astype(float)
        df = df.sort_index(ascending=False)

        # === INDICADORES ===
        df["rsi"] = ta.momentum.RSIIndicator(df["close"]).rsi()
        df["ema9"] = ta.trend.EMAIndicator(df["close"], window=9).ema_indicator()
        df["ema21"] = ta.trend.EMAIndicator(df["close"], window=21).ema_indicator()
        df["macd"] = ta.trend.MACD(df["close"]).macd()
        df["boll_h"] = ta.volatility.BollingerBands(df["close"]).bollinger_hband()
        df["boll_l"] = ta.volatility.BollingerBands(df["close"]).bollinger_lband()
        df["adx"] = ta.trend.ADXIndicator(df["high"], df["low"], df["close"]).adx()
        df["stoch"] = ta.momentum.StochasticOscillator(df["high"], df["low"], df["close"]).stoch()

        last = df.iloc[-1]

        # === CONFLUÊNCIAS ===
        confluencias = []
        if last["rsi"] < 30: confluencias.append("RSI sobrevendido")
        if last["rsi"] > 70: confluencias.append("RSI sobrecomprado")
        if last["ema9"] > last["ema21"]: confluencias.append("Tendência de alta")
        if last["ema9"] < last["ema21"]: confluencias.append("Tendência de baixa")
        if last["macd"] > 0: confluencias.append("MACD positivo")
        if last["macd"] < 0: confluencias.append("MACD negativo")
        if last["close"] <= last["boll_l"]: confluencias.append("Preço na banda inferior")
        if last["close"] >= last["boll_h"]: confluencias.append("Preço na banda superior")

        # === SINAL ===
        signal = "CALL" if len([c for c in confluencias if "alta" in c or "inferior" in c]) >= 2 else "PUT"
        confidence = min(99, 85 + len(confluencias) * 2)

        # === ENVIO PARA TELEGRAM ===
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            msg = f"📊 *{broker}* | {symbol}\n💡 Sinal: *{signal}*\n📈 Confluências: {', '.join(confluencias)}\n🎯 Confiança: {confidence}%"
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

        return {
            "broker": broker,
            "symbol": symbol,
            "signal": signal,
            "confidence": confidence,
            "confluencias": confluencias,
            "last_price": last["close"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ======================================================
# 🚀 EXECUÇÃO LOCAL
# ======================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
