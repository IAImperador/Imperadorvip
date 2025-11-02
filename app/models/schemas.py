from pydantic import BaseModel, Field
from typing import List, Optional, Literal
MarketType = Literal["otc","open"]
class AnalyzeRequest(BaseModel):
    api_key: str
    broker: str
    asset: str
    timeframe: str
    candles: int = 200
    market_type: MarketType = "open"
    mode: Literal["manual","auto"] = "manual"
    min_signals: int = 5
    min_confidence: float = 0.9
class ConfluenceResult(BaseModel):
    signals: List[str]
    score: float
    summary: str
class AnalyzeResponse(BaseModel):
    ok: bool
    message: str
    next_check_seconds: int = 0
    broker: str
    asset: str
    timeframe: str
    market_type: MarketType
    confluence: ConfluenceResult
    entry_recommendation: Optional[str] = None
class Broker(BaseModel):
    key: str; name: str; supports_otc: bool; assets: List[str]; timeframes: List[str]
class BrokersResponse(BaseModel):
    brokers: List[Broker]
