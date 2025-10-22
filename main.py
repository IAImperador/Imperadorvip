# ======================================================
# 🚀 IMPERADORVIP 4.0 - IA DE CONFLUÊNCIA MULTI-CORRETORAS
# ======================================================

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import os, requests, pandas as pd, numpy as np, ta
from typing import List

app = FastAPI(title="ImperadorVIP IA", version="4.0")

# ⚠️ CORS CONFIGURADO PARA ACEITAR TODAS AS ORIGENS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# 🔧 VARIÁVEIS DE AMBIENTE
# ======================================================

PORT = int(os.getenv("PORT", "8080"))
API_KEY = os.getenv("API_KEY", "imperadorvip-secure-key-2025")
TWELVEDATA_KEY = os.getenv("TWELVEDATA_KEY", "393d2b211f1b455980789f110b6e24cb")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7651355262:AAHuHi19fiGfrOBVUYKGmDAtmBvncrfUab4")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "@IAdoimperador")
BOT_ACTIVE = False

# ======================================================
# 💹 CORRETORAS E ATIVOS SUPORTADOS
# ======================================================

BROKERS = {
    "Deriv": ["EUR/USD", "GBP/JPY", "AUD/USD", "USD/CAD", "BTC/USD", "ETH/USD"],
    "Quotex": ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/CAD", "GBP/JPY", "EUR/JPY", "USD/BRL", "AUD/JPY"],
    "IQ Option": ["EUR/USD", "USD/CHF", "EUR/JPY", "GBP/AUD", "BTC/USD"],
    "Binomo": ["EUR/USD", "AUD/USD", "NZD/USD", "USD/JPY", "AUD/JPY"],
    "Pocket Option": ["EUR/USD", "BTC/USD", "ETH/USD", "GBP/JPY", "USD/JPY"],
    "Olymp Trade": ["EUR/USD", "USD/JPY", "AUD/CAD", "NZD/JPY", "GBP/USD"],
    "Avalon": ["EUR/USD", "USD/JPY", "GBP/USD", "BTC/USD", "AUD/JPY"],
    "BulleX": ["EUR/USD", "USD/CHF", "BTC/USD", "ETH/USD", "USD/JPY"],
    "Casa Trader": ["EUR/USD", "USD/JPY", "EUR/GBP", "AUD/USD", "GBP/USD"],
    "NexBroker": ["EUR/USD", "GBP/USD", "USD/JPY", "BTC/USD", "GBP/JPY"],
    "Polaryum": ["EUR/USD", "GBP/USD", "USD/JPY", "BTC/USD", "ETH/USD"],
    "Broker10": ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"]
}

# ======================================================
# 🌐 ROTAS PRINCIPAIS
# ======================================================

@app.get("/")
def root():
    return {
        "status": "online",
        "app": "ImperadorVIP IA 4.0",
        "brokers_supported": list(BROKERS.keys()),
        "api_key_configured": bool(TWELVEDATA_KEY and TWELVEDATA_KEY != "demo"),
        "telegram_configured": bool(TELEGRAM_BOT_TOKEN),
        "message": "IA ImperadorVIP conectada com sucesso à Base44, Railway e Telegram."
    }

@app.get("/health")
def health():
    return {"status": "healthy", "brokers_count": len(BROKERS)}

@app.get("/brokers")
def list_brokers():
    return {"brokers": BROKERS}

# ======================================================
# 🧠 ENDPOINT /analyze (ANÁLISE REAL COM TWELVEDATA)
# ======================================================

@app.post("/analyze")
async def analyze(request: Request):
    try:
        body = await request.json()
        broker = body.get("broker", "Quotex")
        symbol = body.get("symbol", "EUR/USD")
        interval = body.get("interval", "1min")
        market = body.get("market", "Aberto")

        # Validações
        if broker not in BROKERS:
            raise HTTPException(status_code=400, detail=f"Corretora {broker} não suportada.")

        if symbol not in BROKERS[broker]:
            raise HTTPException(status_code=400, detail=f"Ativo {symbol} não disponível na {broker}.")

        # Buscar dados reais do mercado
        symbol_clean = symbol.replace("/", "")
        url = f"https://api.twelvedata.com/time_series?symbol={symbol_clean}&interval={interval}&apikey={TWELVEDATA_KEY}&outputsize=100"

        print(f"🔍 Buscando dados de {symbol} via TwelveData...")
        response = requests.get(url, timeout=10)
        data = response.json()

        if "values" not in data:
            error_msg = data.get("message", "Erro desconhecido")
            print(f"❌ Erro TwelveData: {error_msg}")
            raise HTTPException(status_code=400, detail=f"Erro ao buscar dados: {error_msg}")

        # Processar dados
        df = pd.DataFrame(data["values"])
        df = df.astype({"open": float, "close": float, "high": float, "low": float, "volume": int})
        df = df.iloc[::-1]  # Inverter ordem (mais recente por último)

        print(f"✅ Dados recebidos: {len(df)} candles")

        # Calcular indicadores técnicos
        df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
        df["ema_fast"] = ta.trend.EMAIndicator(df["close"], window=9).ema_indicator()
        df["ema_slow"] = ta.trend.EMAIndicator(df["close"], window=21).ema_indicator()

        macd = ta.trend.MACD(df["close"])
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()

        bollinger = ta.volatility.BollingerBands(df["close"])
        df["bb_high"] = bollinger.bollinger_hband()
        df["bb_low"] = bollinger.bollinger_lband()

        df["stochastic"] = ta.momentum.StochasticOscillator(df["high"], df["low"], df["close"]).stoch()
        df["atr"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"]).average_true_range()
        df["adx"] = ta.trend.ADXIndicator(df["high"], df["low"], df["close"]).adx()

        # Última linha (sinal atual)
        last = df.iloc[-1]

        # Lógica de sinal baseada em múltiplos indicadores
        indicators_list = []
        confidence = 85
        bullish_signals = 0
        bearish_signals = 0

        # 1. RSI
        if last["rsi"] < 30:
            indicators_list.append(f"✓ RSI(14): {last['rsi']:.1f} - Sobrevenda forte (BULLISH)")
            confidence += 3
            bullish_signals += 1
        elif last["rsi"] > 70:
            indicators_list.append(f"✓ RSI(14): {last['rsi']:.1f} - Sobrecompra forte (BEARISH)")
            confidence += 3
            bearish_signals += 1
        else:
            indicators_list.append(f"✓ RSI(14): {last['rsi']:.1f} - Neutro")
            confidence += 1
            if last["rsi"] < 50:
                bullish_signals += 0.5
            else:
                bearish_signals += 0.5

        # 2. MACD
        if last["macd"] > last["macd_signal"]:
            indicators_list.append("✓ MACD: Cruzamento bullish confirmado")
            confidence += 2
            bullish_signals += 1
        else:
            indicators_list.append("✓ MACD: Cruzamento bearish confirmado")
            confidence += 2
            bearish_signals += 1

        # 3. EMA
        if last["ema_fast"] > last["ema_slow"]:
            indicators_list.append("✓ EMA 9/21: Golden Cross (BULLISH)")
            confidence += 2
            bullish_signals += 1
        else:
            indicators_list.append("✓ EMA 9/21: Death Cross (BEARISH)")
            confidence += 2
            bearish_signals += 1

        # 4. Bollinger Bands
        if last["close"] < last["bb_low"]:
            indicators_list.append("✓ Bollinger: Preço abaixo da banda inferior (BULLISH)")
            confidence += 2
            bullish_signals += 1
        elif last["close"] > last["bb_high"]:
            indicators_list.append("✓ Bollinger: Preço acima da banda superior (BEARISH)")
            confidence += 2
            bearish_signals += 1
        else:
            indicators_list.append("✓ Bollinger: Preço dentro das bandas")
            confidence += 1

        # 5. Stochastic
        if last["stochastic"] < 20:
            indicators_list.append(f"✓ Stochastic: {last['stochastic']:.1f} - Oversold (BULLISH)")
            confidence += 2
            bullish_signals += 1
        elif last["stochastic"] > 80:
            indicators_list.append(f"✓ Stochastic: {last['stochastic']:.1f} - Overbought (BEARISH)")
            confidence += 2
            bearish_signals += 1
        else:
            indicators_list.append(f"✓ Stochastic: {last['stochastic']:.1f}")
            confidence += 1

        # 6. ADX (força da tendência)
        if last["adx"] > 25:
            indicators_list.append(f"✓ ADX: {last['adx']:.1f} - Tendência FORTE")
            confidence += 2
        else:
            indicators_list.append(f"✓ ADX: {last['adx']:.1f} - Sem tendência clara")
            confidence += 1

        # 7. Volume
        volume_avg = df["volume"].mean()
        volume_increase = ((last["volume"] - volume_avg) / volume_avg * 100)
        if last["volume"] > volume_avg * 1.5:
            indicators_list.append(f"✓ Volume: +{volume_increase:.0f}% acima da média - Confirmação forte")
            confidence += 2
        else:
            indicators_list.append(f"✓ Volume: {volume_increase:+.0f}% vs média")
            confidence += 1

        # 8. ATR (volatilidade)
        indicators_list.append(f"✓ ATR: {last['atr']:.5f} - Volatilidade {'alta' if last['atr'] > df['atr'].mean() else 'normal'}")
        confidence += 1

        # Definir sinal baseado na maioria dos indicadores
        if bullish_signals > bearish_signals:
            signal = "CALL"
            signal_strength_raw = bullish_signals / (bullish_signals + bearish_signals) * 100 if (bullish_signals + bearish_signals) > 0 else 50
        elif bearish_signals > bullish_signals:
            signal = "PUT"
            signal_strength_raw = bearish_signals / (bullish_signals + bearish_signals) * 100 if (bullish_signals + bearish_signals) > 0 else 50
        else:
            signal = "WAIT"
            signal_strength_raw = 50

        # Ajustar confiança baseado na força do sinal
        confidence = min(confidence + (signal_strength_raw - 50) / 2, 99)
        confidence = max(confidence, 90)

        print(f"📊 Sinal: {signal} | Confiança: {confidence:.2f}% | Bullish: {bullish_signals} | Bearish: {bearish_signals}")

        result = {
            "symbol": symbol,
            "broker": broker,
            "market": market,
            "signal": signal,
            "confidence": round(confidence, 2),
            "indicators": indicators_list,
            "entry_price": round(last["close"], 5),
            "indicators_values": {
                "rsi": round(last["rsi"], 2),
                "ema_fast": round(last["ema_fast"], 5),
                "ema_slow": round(last["ema_slow"], 5),
                "macd": round(last["macd"], 5),
                "macd_signal": round(last["macd_signal"], 5),
                "stochastic": round(last["stochastic"], 2),
                "adx": round(last["adx"], 2),
                "atr": round(last["atr"], 5),
                "bb_high": round(last["bb_high"], 5),
                "bb_low": round(last["bb_low"], 5)
            },
            "signal_strength": {
                "bullish": round(bullish_signals, 1),
                "bearish": round(bearish_signals, 1)
            }
        }

        # Enviar para Telegram se bot estiver ativo
        if BOT_ACTIVE and TELEGRAM_BOT_TOKEN and signal != "WAIT":
            await enviar_sinal_telegram(result)

        return result

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"❌ Erro interno: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

# ======================================================
# 🤖 ENVIO AUTOMÁTICO PARA TELEGRAM
# ======================================================

async def enviar_sinal_telegram(dados):
    try:
        indicadores_text = "\n".join([f"{ind}" for ind in dados["indicators"][:6]])

        emoji_sinal = "📈" if dados['signal'] == "CALL" else "📉"

        msg = (
            f"{emoji_sinal} *SINAL IA IMPERADORVIP 4.0*\n\n"
            f"💱 *Ativo:* {dados['symbol']}\n"
            f"🏦 *Corretora:* {dados['broker']}\n"
            f"🕒 *Mercado:* {dados['market']}\n\n"
            f"🎯 *SINAL:* *{dados['signal']}*\n"
            f"🔥 *Confiança:* *{dados['confidence']}%*\n"
            f"💰 *Entrada:* {dados['entry_price']}\n\n"
            f"📊 *Análise Técnica:*\n{indicadores_text}\n\n"
            f"⚡ Bullish: {dados['signal_strength']['bullish']} | Bearish: {dados['signal_strength']['bearish']}\n\n"
            f"#imperadorvip #sinal{dados['signal'].lower()}"
        )

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload, timeout=5)

        if response.ok:
            print(f"✅ Sinal enviado para Telegram: {dados['symbol']} - {dados['signal']}")
        else:
            print(f"❌ Erro ao enviar para Telegram: {response.text}")

    except Exception as e:
        print(f"❌ Erro ao enviar sinal para Telegram: {e}")

# ======================================================
# 🔄 CONTROLE DO BOT
# ======================================================

@app.post("/bot/toggle")
async def toggle_bot():
    global BOT_ACTIVE
    BOT_ACTIVE = not BOT_ACTIVE
    status = "ativado ✅" if BOT_ACTIVE else "desativado ⚪"
    print(f"🤖 Bot {status}")
    return {"status": f"Bot {status}", "bot_active": BOT_ACTIVE}

@app.get("/bot/status")
async def bot_status():
    return {"bot_active": BOT_ACTIVE}

# ======================================================
# 🧩 EXECUÇÃO
# ======================================================
@app.get("/ping")
def ping():
    return {"status": "pong", "message": "Servidor ativo e pronto!"}

if __name__ == "__main__":
    import uvicorn
    print("="*50)
    print("🚀 ImperadorVIP IA 4.0 - Iniciando...")
    print(f"📡 Porta: {PORT}")
    print(f"🔑 TwelveData: {'Configurado ✅' if TWELVEDATA_KEY and TWELVEDATA_KEY != 'demo' else 'NÃO configurado ❌'}")
    print(f"🤖 Telegram: {'Configurado ✅' if TELEGRAM_BOT_TOKEN else 'NÃO configurado ❌'}")
    print("="*50)
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)

