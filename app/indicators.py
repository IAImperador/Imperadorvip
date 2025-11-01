import ta

def calculate_indicators(df):
    indicators = {
        "rsi": float(ta.momentum.RSIIndicator(df["close"], 14).rsi().iloc[-1]),
        "ema9": float(ta.trend.EMAIndicator(df["close"], 9).ema_indicator().iloc[-1]),
        "ema21": float(ta.trend.EMAIndicator(df["close"], 21).ema_indicator().iloc[-1]),
        "macd": float(ta.trend.MACD(df["close"]).macd().iloc[-1]),
        "boll_high": float(ta.volatility.BollingerBands(df["close"]).bollinger_hband().iloc[-1]),
        "boll_low": float(ta.volatility.BollingerBands(df["close"]).bollinger_lband().iloc[-1])
    }
    return indicators
