from .market import fetch_candles, compute_confluence
def analyze(symbol: str, timeframe: str, candles: int):
    df = fetch_candles(symbol, timeframe, candles)
    return compute_confluence(df)
