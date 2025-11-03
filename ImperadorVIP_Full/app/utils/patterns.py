
import pandas as pd

def is_bullish_engulfing(df: pd.DataFrame) -> pd.Series:
    o, c = df['open'], df['close']
    prev = df.shift(1)
    return (prev['close'] < prev['open']) & (c > o) & (c >= prev['open']) & (o <= prev['close'])

def is_bearish_engulfing(df: pd.DataFrame) -> pd.Series:
    o, c = df['open'], df['close']
    prev = df.shift(1)
    return (prev['close'] > prev['open']) & (c < o) & (c <= prev['open']) & (o >= prev['close'])

def is_hammer(df: pd.DataFrame, ratio: float = 2.5) -> pd.Series:
    o, h, l, c = df['open'], df['high'], df['low'], df['close']
    body = (c - o).abs()
    lower_wick = o.combine(c, min) - l
    upper_wick = h - o.combine(c, max)
    return (lower_wick > ratio * body) & (upper_wick <= body)

def is_shooting_star(df: pd.DataFrame, ratio: float = 2.5) -> pd.Series:
    o, h, l, c = df['open'], df['high'], df['low'], df['close']
    body = (c - o).abs()
    lower_wick = o.combine(c, min) - l
    upper_wick = h - o.combine(c, max)
    return (upper_wick > ratio * body) & (lower_wick <= body)
