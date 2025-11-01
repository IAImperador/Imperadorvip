from __future__ import annotations
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD
from ta.volatility import BollingerBands

def ema(series: pd.Series, window: int=20) -> pd.Series:
    return EMAIndicator(close=series, window=window).ema_indicator()

def rsi(series: pd.Series, window: int=14) -> pd.Series:
    return RSIIndicator(close=series, window=window).rsi()

def macd(series: pd.Series):
    m = MACD(close=series)
    return m.macd(), m.macd_signal(), m.macd_diff()

def bbands(series: pd.Series, window: int=20):
    b = BollingerBands(close=series, window=window, window_dev=2)
    return b.bollinger_hband(), b.bollinger_lband(), b.bollinger_mavg()

def detect_candles(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    o,c,h,l = df['open'],df['close'],df['high'],df['low']
    body = (c - o).abs()
    upper_wick = (h - np.maximum(c,o))
    lower_wick = (np.minimum(c,o) - l)
    df['pinbar_bull'] = (lower_wick > 2.5*body) & (c>o)
    df['pinbar_bear'] = (upper_wick > 2.5*body) & (c<o)
    prev_o, prev_c = o.shift(1), c.shift(1)
    df['engolfo_bull'] = (c>o) & (prev_c<prev_o) & (c>=prev_o) & (o<=prev_c)
    df['engolfo_bear'] = (c<o) & (prev_c>prev_o) & (o>=prev_c) & (c<=prev_o)
    df['martelo'] = (lower_wick >= 2*body)
    df['estrela_cadente'] = (upper_wick >= 2*body)
    return df
