from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import ta
from datetime import datetime, timedelta
import requests
import os
from typing import Optional
from pydantic import BaseModel

app = FastAPI(title="IA ImperadorVIP - Real Technical Analysis")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurações
API_KEY = os.getenv("API_KEY", "imperadorvip-secure-key-2025")
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY", "e83d8d2c7b7f4c9d98f8e9c3e4d5f6a7")

BROKERS_ENABLED = [
    "Deriv", "Quotex", "IQ Option", "Binomo", "Pocket Option",
    "Olymp Trade", "Avalon", "BulleX", "Casa Trader", "NexBroker",
    "Polarium", "Broker10"
]

# Modelos
class AnalyzeRequest(BaseModel):
    asset: str
    broker: str
    timeframe: str = "M5"
    market_type: str = "Aberto"

def verify_api_key(x_api_key: Optional[str] = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="API Key inválida")
    return True

@app.get("/")
def read_root():
    return {"message": "IA ImperadorVIP API - Sistema de Análise Técnica Real"}

@app.get("/health")
def health_check():
    return {
        "status": "online",
        "app": "ImperadorVIP",
        "brokers_enabled": BROKERS_ENABLED,
        "message": "IA ImperadorVIP conectada com sucesso à Base44."
    }

def get_historical_data(symbol: str, interval: str = "5min", outputsize: int = 100):
    """Buscar dados históricos da TwelveData"""
    try:
        symbol_clean = symbol.replace("/", "")
        url = "https://api.twelvedata.com/time_series"
        params = {
            "symbol": symbol_clean,
            "interval": interval,
            "outputsize": outputsize,
            "apikey": TWELVEDATA_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if "values" not in data:
            return None
        
        df = pd.DataFrame(data["values"])
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.sort_values("datetime")
        
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col])
        
        return df
    except Exception as e:
        print(f"Erro ao buscar dados: {e}")
        return None

def calculate_all_indicators(df: pd.DataFrame):
    """Calcular TODOS os indicadores técnicos"""
    if df is None or len(df) < 50:
        return None
    
    indicators = {}
    
    try:
        # RSI
        indicators["rsi_14"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi().iloc[-1]
        indicators["rsi_9"] = ta.momentum.RSIIndicator(df["close"], window=9).rsi().iloc[-1]
        
        # MACD
        macd = ta.trend.MACD(df["close"])
        indicators["macd"] = macd.macd().iloc[-1]
        indicators["macd_signal"] = macd.macd_signal().iloc[-1]
        indicators["macd_diff"] = macd.macd_diff().iloc[-1]
        
        # Bollinger Bands
        bollinger = ta.volatility.BollingerBands(df["close"])
        indicators["bb_high"] = bollinger.bollinger_hband().iloc[-1]
        indicators["bb_mid"] = bollinger.bollinger_mavg().iloc[-1]
        indicators["bb_low"] = bollinger.bollinger_lband().iloc[-1]
        indicators["bb_width"] = bollinger.bollinger_wband().iloc[-1]
        
        # Stochastic
        stoch = ta.momentum.StochasticOscillator(df["high"], df["low"], df["close"])
        indicators["stoch_k"] = stoch.stoch().iloc[-1]
        indicators["stoch_d"] = stoch.stoch_signal().iloc[-1]
        
        # ATR
        indicators["atr"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"]).average_true_range().iloc[-1]
        
        # ADX
        indicators["adx"] = ta.trend.ADXIndicator(df["high"], df["low"], df["close"]).adx().iloc[-1]
        
        # CCI
        indicators["cci"] = ta.trend.CCIIndicator(df["high"], df["low"], df["close"]).cci().iloc[-1]
        
        # Williams %R
        indicators["williams_r"] = ta.momentum.WilliamsRIndicator(df["high"], df["low"], df["close"]).williams_r().iloc[-1]
        
        # MFI
        indicators["mfi"] = ta.volume.MFIIndicator(df["high"], df["low"], df["close"], df["volume"]).money_flow_index().iloc[-1]
        
        # EMA
        indicators["ema_9"] = ta.trend.EMAIndicator(df["close"], window=9).ema_indicator().iloc[-1]
        indicators["ema_21"] = ta.trend.EMAIndicator(df["close"], window=21).ema_indicator().iloc[-1]
        indicators["ema_50"] = ta.trend.EMAIndicator(df["close"], window=50).ema_indicator().iloc[-1]
        
        # SMA
        indicators["sma_20"] = ta.trend.SMAIndicator(df["close"], window=20).sma_indicator().iloc[-1]
        indicators["sma_50"] = ta.trend.SMAIndicator(df["close"], window=50).sma_indicator().iloc[-1]
        
        # Volume
        indicators["volume_sma"] = df["volume"].rolling(window=20).mean().iloc[-1]
        indicators["volume_current"] = df["volume"].iloc[-1]
        
        # Preço atual
        indicators["current_price"] = df["close"].iloc[-1]
        indicators["previous_close"] = df["close"].iloc[-2]
        
        return indicators
    except Exception as e:
        print(f"Erro ao calcular indicadores: {e}")
        return None

def detect_confluences(indicators: dict):
    """Detectar confluências (mínimo 5 para gerar sinal)"""
    confluences = []
    bullish_score = 0
    bearish_score = 0
    
    # 1. RSI
    if indicators["rsi_14"] < 30:
        confluences.append("RSI Oversold (< 30)")
        bullish_score += 15
    elif indicators["rsi_14"] > 70:
        confluences.append("RSI Overbought (> 70)")
        bearish_score += 15
    
    # 2. MACD
    if indicators["macd_diff"] > 0 and indicators["macd"] > indicators["macd_signal"]:
        confluences.append("MACD Bullish Crossover")
        bullish_score += 12
    elif indicators["macd_diff"] < 0 and indicators["macd"] < indicators["macd_signal"]:
        confluences.append("MACD Bearish Crossover")
        bearish_score += 12
    
    # 3. Bollinger Bands
    current_price = indicators["current_price"]
    if current_price <= indicators["bb_low"]:
        confluences.append("Price at Lower Bollinger Band")
        bullish_score += 10
    elif current_price >= indicators["bb_high"]:
        confluences.append("Price at Upper Bollinger Band")
        bearish_score += 10
    
    # 4. Stochastic
    if indicators["stoch_k"] < 20:
        confluences.append("Stochastic Oversold (< 20)")
        bullish_score += 10
    elif indicators["stoch_k"] > 80:
        confluences.append("Stochastic Overbought (> 80)")
        bearish_score += 10
    
    # 5. EMA Crossover
    if indicators["ema_9"] > indicators["ema_21"] > indicators["ema_50"]:
        confluences.append("EMA Bullish Alignment (9>21>50)")
        bullish_score += 12
    elif indicators["ema_9"] < indicators["ema_21"] < indicators["ema_50"]:
        confluences.append("EMA Bearish Alignment (9<21<50)")
        bearish_score += 12
    
    # 6. ADX
    if indicators["adx"] > 25:
        confluences.append(f"Strong Trend Detected (ADX {indicators['adx']:.1f})")
        if bullish_score > bearish_score:
            bullish_score += 8
        else:
            bearish_score += 8
    
    # 7. Volume
    if indicators["volume_current"] > indicators["volume_sma"] * 1.5:
        confluences.append("High Volume Spike (1.5x average)")
        if bullish_score > bearish_score:
            bullish_score += 8
        else:
            bearish_score += 8
    
    # 8. Williams %R
    if indicators["williams_r"] < -80:
        confluences.append("Williams %R Oversold")
        bullish_score += 8
    elif indicators["williams_r"] > -20:
        confluences.append("Williams %R Overbought")
        bearish_score += 8
    
    # 9. MFI
    if indicators["mfi"] < 20:
        confluences.append("Money Flow Index Oversold")
        bullish_score += 8
    elif indicators["mfi"] > 80:
        confluences.append("Money Flow Index Overbought")
        bearish_score += 8
    
    # 10. Price Action
    price_change = ((indicators["current_price"] - indicators["previous_close"]) / indicators["previous_close"]) * 100
    if price_change < -1:
        confluences.append(f"Strong Bearish Candle ({price_change:.2f}%)")
        bearish_score += 6
    elif price_change > 1:
        confluences.append(f"Strong Bullish Candle ({price_change:.2f}%)")
        bullish_score += 6
    
    return confluences, bullish_score, bearish_score

@app.post("/analyze")
async def analyze_signal(request: AnalyzeRequest, x_api_key: Optional[str] = Header(None)):
    """Endpoint principal de análise técnica"""
    
    # Verificar API Key
    verify_api_key(x_api_key)
    
    try:
        # Mapear timeframe
        interval_map = {
            "M1": "1min",
            "M5": "5min",
            "M15": "15min",
            "M30": "30min",
            "H1": "1h"
        }
        interval = interval_map.get(request.timeframe, "5min")
        
        # 1. Buscar dados históricos
        df = get_historical_data(request.asset, interval=interval, outputsize=100)
        if df is None:
            raise HTTPException(status_code=500, detail="Erro ao buscar dados históricos")
        
        # 2. Calcular indicadores
        indicators = calculate_all_indicators(df)
        if indicators is None:
            raise HTTPException(status_code=500, detail="Erro ao calcular indicadores")
        
        # 3. Detectar confluências
        confluences, bullish_score, bearish_score = detect_confluences(indicators)
        
        # 4. REGRA: Mínimo 5 confluências para gerar sinal
        if len(confluences) < 5:
            return {
                "error": True,
                "message": f"Apenas {len(confluences)} confluências detectadas. Mínimo necessário: 5",
                "confluences": confluences,
                "confidence_score": 0
            }
        
        # 5. Determinar direção do sinal
        signal_type = "CALL" if bullish_score > bearish_score else "PUT"
        confidence_score = max(bullish_score, bearish_score)
        
        # 6. REGRA: Confiança mínima 85%
        if confidence_score < 85:
            return {
                "error": True,
                "message": f"Confiança muito baixa ({confidence_score}%). Mínimo necessário: 85%",
                "confluences": confluences,
                "confidence_score": confidence_score
            }
        
        # 7. Calcular entrada, stop loss e take profit
        current_price = indicators["current_price"]
        atr = indicators["atr"]
        
        if signal_type == "CALL":
            entry_price = current_price
            stop_loss = current_price - (atr * 2)
            take_profit = current_price + (atr * 3)
        else:
            entry_price = current_price
            stop_loss = current_price + (atr * 2)
            take_profit = current_price - (atr * 3)
        
        # 8. Análise descritiva
        analysis = f"Análise técnica em {request.asset} identificou {len(confluences)} confluências com {confidence_score}% de confiança. "
        analysis += f"Sinal {signal_type} recomendado. "
        analysis += f"Principais confluências: {', '.join(confluences[:3])}."
        
        return {
            "signal_type": signal_type,
            "entry_price": float(entry_price),
            "stop_loss": float(stop_loss),
            "take_profit": float(take_profit),
            "confidence_score": int(confidence_score),
            "confluences": confluences,
            "analysis": analysis,
            "indicators": {k: float(v) if isinstance(v, (int, float, np.number)) else str(v) 
                          for k, v in indicators.items()},
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na análise: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)        
        # Preço atual
        indicators["current_price"] = df["close"].iloc[-1]
        
        return indicators
    
    except Exception as e:
        print(f"Erro ao calcular indicadores: {e}")
        return None

def analyze_confluences(indicators: dict, df: pd.DataFrame):
    """
    Analisar confluências baseadas em indicadores REAIS
    Retorna: (signal_type, confidence, confluences[])
    """
    confluences = []
    call_score = 0
    put_score = 0
    
    current_price = indicators["current_price"]
    
    # 1. RSI
    if indicators["rsi_14"] < 30:
        confluences.append("RSI em sobrevenda (< 30)")
        call_score += 2
    elif indicators["rsi_14"] > 70:
        confluences.append("RSI em sobrecompra (> 70)")
        put_score += 2
    
    # 2. MACD
    if indicators["macd"] > indicators["macd_signal"] and indicators["macd_diff"] > 0:
        confluences.append("MACD cruzamento otimista")
        call_score += 2
    elif indicators["macd"] < indicators["macd_signal"] and indicators["macd_diff"] < 0:
        confluences.append("MACD cruzamento pessimista")
        put_score += 2
    
    # 3. Bollinger Bands
    if current_price <= indicators["bb_low"]:
        confluences.append("Preço tocando Bollinger inferior")
        call_score += 1
    elif current_price >= indicators["bb_high"]:
        confluences.append("Preço tocando Bollinger superior")
        put_score += 1
    
    # 4. Stochastic
    if indicators["stoch_k"] < 20:
        confluences.append("Stochastic em zona de sobrevenda")
        call_score += 1
    elif indicators["stoch_k"] > 80:
        confluences.append("Stochastic em zona de sobrecompra")
        put_score += 1
    
    # 5. ADX (força da tendência)
    if indicators["adx"] > 25:
        confluences.append(f"Tendência forte (ADX {indicators['adx']:.1f})")
        if call_score > put_score:
            call_score += 1
        else:
            put_score += 1
    
    # 6. Volume (OBV)
    if indicators["obv"] > 0:
        confluences.append("Volume acima da média")
        if call_score > put_score:
            call_score += 1
        else:
            put_score += 1
    
    # 7. EMA Cruzamento
    if indicators["ema_9"] > indicators["ema_21"]:
        confluences.append("EMA 9 acima da EMA 21")
        call_score += 1
    elif indicators["ema_9"] < indicators["ema_21"]:
        confluences.append("EMA 9 abaixo da EMA 21")
        put_score += 1
    
    # 8. Parabolic SAR
    if indicators["psar"] < current_price:
        confluences.append("Parabolic SAR suporta alta")
        call_score += 1
    else:
        confluences.append("Parabolic SAR suporta baixa")
        put_score += 1
    
    # 9. CCI
    if indicators["cci"] < -100:
        confluences.append("CCI indica sobrevenda")
        call_score += 1
    elif indicators["cci"] > 100:
        confluences.append("CCI indica sobrecompra")
        put_score += 1
    
    # 10. Williams %R
    if indicators["williams_r"] < -80:
        confluences.append("Williams %R sobrevenda")
        call_score += 1
    elif indicators["williams_r"] > -20:
        confluences.append("Williams %R sobrecompra")
        put_score += 1
    
    # Determinar sinal
    if call_score > put_score and len(confluences) >= 5:
        signal_type = "CALL"
        confidence = min(95, 70 + (call_score * 2))
    elif put_score > call_score and len(confluences) >= 5:
        signal_type = "PUT"
        confidence = min(95, 70 + (put_score * 2))
    else:
        return None, 0, []
    
    return signal_type, confidence, confluences

@app.post("/analyze")
async def analyze_signal(
    asset: str,
    broker: str,
    timeframe: str = "M5",
    x_api_key: str = Header(None)
):
    """
    Endpoint para análise técnica REAL
    """
    verify_api_key(x_api_key)
    
    # Converter timeframe
    interval_map = {
        "M1": "1min",
        "M5": "5min",
        "M15": "15min",
        "M30": "30min",
        "H1": "1h"
    }
    interval = interval_map.get(timeframe, "5min")
    
    # Buscar dados históricos
    df = get_historical_data(asset, interval, outputsize=200)
    
    if df is None:
        raise HTTPException(status_code=500, detail="Erro ao buscar dados históricos")
    
    # Calcular indicadores
    indicators = calculate_all_indicators(df)
    
    if indicators is None:
        raise HTTPException(status_code=500, detail="Erro ao calcular indicadores")
    
    # Analisar confluências
    signal_type, confidence, confluences = analyze_confluences(indicators, df)
    
    if signal_type is None:
        return {
            "status": "no_signal",
            "message": "Não há confluências suficientes (mínimo 5)"
        }
    
    # Calcular Stop Loss e Take Profit
    atr = indicators["atr"]
    entry_price = indicators["current_price"]
    
    if signal_type == "CALL":
        stop_loss = entry_price - (atr * 1.5)
        take_profit = entry_price + (atr * 2.5)
    else:
        stop_loss = entry_price + (atr * 1.5)
        take_profit = entry_price - (atr * 2.5)
    
    result = {
        "status": "success",
        "signal_type": signal_type,
        "asset": asset,
        "broker": broker,
        "timeframe": timeframe,
        "entry_price": round(entry_price, 5),
        "stop_loss": round(stop_loss, 5),
        "take_profit": round(take_profit, 5),
        "confidence_score": int(confidence),
        "confluences": confluences,
        "indicators": {
            "rsi": round(indicators["rsi_14"], 2),
            "macd": round(indicators["macd"], 5),
            "atr": round(indicators["atr"], 5),
            "adx": round(indicators["adx"], 2)
        },
        "analysis": f"Análise técnica completa com {len(confluences)} confluências detectadas.",
        "timestamp": datetime.now().isoformat()
    }
    
    # Se tiver webhook configurado, enviar para Base44
    if BASE44_WEBHOOK_URL:
        try:
            requests.post(BASE44_WEBHOOK_URL, json=result, timeout=5)
        except:
            pass
    
    return result

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)


