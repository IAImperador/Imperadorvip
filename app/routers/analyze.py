from fastapi import APIRouter, HTTPException
from ..models.schemas import AnalyzeRequest, AnalyzeResponse, ConfluenceResult, BrokersResponse, Broker
from ..config import settings
from ..services.confluence import analyze
from ..brokers import SUPPORTED_BROKERS

router = APIRouter(tags=["analyze"])

@router.get("/brokers", response_model=BrokersResponse)
def list_brokers():
    return {"brokers":[Broker(key=k, name=v["name"], supports_otc=v["supports_otc"], assets=v["assets"], timeframes=v["timeframes"]) for k,v in SUPPORTED_BROKERS.items()]}

def _validate(req: AnalyzeRequest):
    if req.api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="API_KEY inválida")
    if req.broker not in SUPPORTED_BROKERS:
        raise HTTPException(status_code=400, detail="Corretora não suportada")
    broker = SUPPORTED_BROKERS[req.broker]
    if req.asset not in broker["assets"]:
        raise HTTPException(status_code=400, detail="Ativo não suportado")
    return broker

@router.post("/analyze/manual", response_model=AnalyzeResponse)
def analyze_manual(req: AnalyzeRequest):
    _validate(req)
    signals, score, summary, direction = analyze(req.asset, req.timeframe, req.candles)
    ok = (len(signals) >= req.min_signals) and (score >= req.min_confidence)
    entry = None
    if ok:
        entry = "CALL" if "CALL" in " ".join(signals) and "PUT" not in " ".join(signals) else ("PUT" if "PUT" in " ".join(signals) and "CALL" not in " ".join(signals) else "NEUTRAL")
    return AnalyzeResponse(ok=ok, message="Análise manual", next_check_seconds=0, broker=req.broker, asset=req.asset, timeframe=req.timeframe, market_type=req.market_type, confluence=ConfluenceResult(signals=signals, score=score, summary=summary), entry_recommendation=entry)

@router.post("/analyze/auto", response_model=AnalyzeResponse)
def analyze_auto(req: AnalyzeRequest):
    _validate(req)
    signals, score, summary, direction = analyze(req.asset, req.timeframe, req.candles)
    ok = (len(signals) >= req.min_signals) and (score >= req.min_confidence)
    entry = None
    if ok:
        entry = "CALL" if "CALL" in " ".join(signals) and "PUT" not in " ".join(signals) else ("PUT" if "PUT" in " ".join(signals) and "CALL" not in " ".join(signals) else "NEUTRAL")
    return AnalyzeResponse(ok=ok, message="Análise automática", next_check_seconds=300, broker=req.broker, asset=req.asset, timeframe=req.timeframe, market_type=req.market_type, confluence=ConfluenceResult(signals=signals, score=score, summary=summary), entry_recommendation=entry)
