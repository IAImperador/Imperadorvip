def detect_patterns(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    body = abs(last["close"] - last["open"])
    shadow = abs(last["high"] - last["low"])

    if body < (shadow * 0.25):
        return "Doji"
    elif last["close"] > last["open"] and prev["close"] < prev["open"]:
        return "Bullish Engulfing"
    elif last["close"] < last["open"] and prev["close"] > prev["open"]:
        return "Bearish Engulfing"
    else:
        return "Neutral"
