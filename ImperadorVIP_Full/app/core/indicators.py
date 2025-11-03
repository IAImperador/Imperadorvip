
import numpy as np
import pandas as pd

def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=max(1, window//2)).mean()

def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / (loss.replace(0, np.nan))
    return (100 - (100 / (1 + rs))).fillna(50)

def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    fast_ema = ema(close, fast)
    slow_ema = ema(close, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def bollinger(close: pd.Series, window: int = 20, num_std: float = 2.0):
    ma = sma(close, window)
    std = close.rolling(window=window, min_periods=max(1, window//2)).std()
    upper = ma + num_std * std
    lower = ma - num_std * std
    return upper, ma, lower

def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series):
    typical_price = (high + low + close) / 3.0
    cum_vol = volume.cumsum().replace(0, np.nan)
    cum_tp_vol = (typical_price * volume).cumsum()
    return (cum_tp_vol / cum_vol).fillna(method="bfill").fillna(method="ffill")
