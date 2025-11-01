from __future__ import annotations
import os, json
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .sinais import gerar_sinal

load_dotenv()
API_KEY = os.getenv("API_KEY", "")
TWELVEDATA_KEY = os.getenv("TWELVEDATA_KEY")
MARKET_MODE_DEFAULT = os.getenv("MARKET_MODE", "open").lower()
ALLOW_ORIGINS = os.getenv("ALLOW_ORIGINS", "*")

app = FastAPI(title="Imperador VIP", version="4.0")

app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in ALLOW_ORIGINS.split(",")] if ALLOW_ORIGINS else ["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def require_key(x_api_key: str = Header(None)):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="API key inválida")

class LiveRequest(BaseModel):
    broker: str
    symbol: str
    timeframe: str = "5"
    market_mode: str | None = None
    manual: bool = True
    extras: dict | None = None

@app.get("/health")
async def health():
    return {"status":"ok"}

@app.post("/signal/live")
async def signal_live(req: LiveRequest, _: None = Depends(require_key)):
    market = (req.market_mode or MARKET_MODE_DEFAULT).lower()
    if market not in ("open","otc"):
        raise HTTPException(400, "market_mode deve ser 'open' ou 'otc'")
    if not TWELVEDATA_KEY:
        raise HTTPException(500, "TWELVEDATA_KEY não configurada")
    sinal = await gerar_sinal(req.symbol, req.timeframe, TWELVEDATA_KEY, market)
    return {"ok": True, "sinal": sinal}

# Agendador automático (5 min) — apenas loga quando score >= 90
scheduler = AsyncIOScheduler()

async def job_auto():
    watch = [{"broker":"IQOption","symbol":"EUR/USD","tf":"5","market":MARKET_MODE_DEFAULT},
             {"broker":"Deriv","symbol":"USD/JPY","tf":"5","market":MARKET_MODE_DEFAULT}]
    out = []
    for w in watch:
        try:
            s = await gerar_sinal(w["symbol"], w["tf"], TWELVEDATA_KEY, w["market"])
            if s["confluencia"]["score"] >= 90:
                out.append(s)
        except Exception as e:
            out.append({"symbol": w["symbol"], "erro": str(e)})
    print("AUTO-5MIN", json.dumps(out, ensure_ascii=False))

@app.on_event("startup")
async def start():
    scheduler.add_job(job_auto, "interval", minutes=5, id="auto5", replace_existing=True)
    scheduler.start()
