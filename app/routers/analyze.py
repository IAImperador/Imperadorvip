import random

def analyze_signal(pair: str, timeframe: str, market: str):
    # Simulação realista — depois conecta com indicadores reais
    patterns = ["Pinbar", "Engolfo", "Martelo", "Estrela Cadente", "Doji"]
    indicators = ["RSI", "MACD", "VWAP", "Médias Móveis", "Bandas de Bollinger"]

    confluences = random.randint(5, 10)
    confidence = random.randint(90, 98)

    signal_type = "CALL" if random.choice([True, False]) else "PUT"

    return {
        "signal": signal_type,
        "patterns": random.sample(patterns, 2),
        "indicators": random.sample(indicators, 3),
        "confluences": confluences,
        "confidence": f"{confidence}%",
        "entry_time": "agora",
        "market": market,
    }
