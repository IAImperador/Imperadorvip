import requests
from statistics import mean
TD_BASE = "https://api.twelvedata.com"

def _fetch_series(symbol: str, interval: str, api_key: str, points: int = 100):
    params = {"symbol":symbol,"interval":interval,"apikey":api_key,"outputsize":str(points),"format":"JSON","dp":"5"}
    r = requests.get(f"{TD_BASE}/time_series", params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    if "values" not in data: raise ValueError(f"TwelveData sem 'values': {data}")
    vals = data["values"]
    vals_sorted = sorted(vals, key=lambda x: x["datetime"])
    for v in vals_sorted: v["close"] = float(v["close"])
    return vals_sorted

def sma(values, length):
    from statistics import mean
    return mean(values[-length:]) if len(values)>=length else None

def rsi(values, length=14):
    if len(values) < length + 1: return None
    gains, losses = [], []
    for i in range(-length, 0):
        diff = values[i] - values[i-1]
        (gains if diff>=0 else losses).append(abs(diff))
    avg_gain = (sum(gains)/len(gains)) if gains else 0.0
    avg_loss = (sum(losses)/len(losses)) if losses else 0.0
    if avg_loss == 0: return 100.0
    rs = avg_gain/avg_loss
    return 100 - (100/(1+rs))

def build_signal(symbol: str, interval: str, api_key: str, min_conf: int = 90):
    series = _fetch_series(symbol, interval, api_key, points=120)
    closes = [c["close"] for c in series]
    sma9 = sma(closes, 9); sma21 = sma(closes,21); rsi14 = rsi(closes,14)
    confluences, score = [], 0
    if sma9 is not None and sma21 is not None:
        if sma9 > sma21: confluences.append("SMA9>SMA21 (viés compra)"); score += 35
        elif sma9 < sma21: confluences.append("SMA9<SMA21 (viés venda)"); score += 35
    if rsi14 is not None:
        if rsi14 < 30: confluences.append("RSI<30 (sobrevenda)"); score += 35
        elif rsi14 > 70: confluences.append("RSI>70 (sobrecompra)"); score += 35
        else: confluences.append("RSI neutro (30–70)"); score += 15
    if len(closes) >= 4:
        ups = int(closes[-1] > closes[-2]) + int(closes[-2] > closes[-3])
        if ups >= 2: confluences.append("Momentum comprador 3 velas"); score += 30
        else: confluences.append("Momentum vendedor 3 velas"); score += 30
    confidence = min(99, score)
    if confluences:
        side = "CALL" if "SMA9>SMA21" in confluences[0] else ("PUT" if "SMA9<SMA21" in confluences[0] else ("CALL" if closes[-1]>closes[-2] else "PUT"))
    else:
        side = "CALL"
    ok = confidence >= min_conf
    return {"ok":ok,"side":side,"confidence":confidence,"confluences":confluences}
