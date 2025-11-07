from pydantic import BaseModel, Field
from typing import Optional, Literal, List

class ToggleRequest(BaseModel):
    api_key: str

class ModeRequest(BaseModel):
    api_key: str
    mode: Literal["manual","auto"]

class MarketRequest(BaseModel):
    api_key: str
    market: Literal["open","otc"]

class SignalRequest(BaseModel):
    api_key: str
    symbol: str = Field(..., examples=["EUR/USD","AAPL","BTC/USD"])
    timeframe: str = Field("5min", examples=["1min","5min","15min","1h"])
    min_confidence: int = 90

class SignalResult(BaseModel):
    ok: bool
    symbol: str
    timeframe: str
    market: Literal["open","otc"]
    mode: Literal["manual","auto"]
    side: Optional[Literal["CALL","PUT","BUY","SELL"]] = None
    confidence: Optional[int] = None
    confluences: List[str] = []
    entry_time: Optional[str] = None
    message: Optional[str] = None
