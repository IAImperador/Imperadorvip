def calculate_confluence(ind, pattern):
    score = 0

    if ind["ema9"] > ind["ema21"] and ind["rsi"] < 70:
        score += 30
    elif ind["ema9"] < ind["ema21"] and ind["rsi"] > 30:
        score += 30

    if ind["macd"] > 0:
        score += 20
    else:
        score += 10

    if ind["boll_high"] and ind["boll_low"]:
        score += 10

    if "Bullish" in pattern:
        score += 30
        signal = "CALL"
    elif "Bearish" in pattern:
        score += 30
        signal = "PUT"
    else:
        signal = "WAIT"

    confidence = min(99, score)
    return confidence, signal
