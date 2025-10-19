import os
import time
from datetime import datetime
from enum import StrEnum
from typing import List, Optional, Literal, Dict, Any

import numpy as np
import pandas as pd
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Header, Request, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import (
    create_engine, String, Integer, Float, BigInteger, DateTime,
    UniqueConstraint, Index, text
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator

# -----------------------------------------------------------------------------
# Carregar env
# -----------------------------------------------------------------------------
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "")
API_KEY_ENV = os.getenv("API_KEY", "")
ASSET_SYNC_MODE = os.getenv("ASSET_SYNC_MODE", "static").lower()

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL não definido.")
if not API_KEY_ENV:
    raise RuntimeError("API_KEY não definido.")

# -----------------------------------------------------------------------------
# Segurança simples com API Key
# -----------------------------------------------------------------------------
def require_api_key(x_api_key: str = Header(default="")):
    if x_api_key != API_KEY_ENV:
        raise HTTPException(status_code=401, detail="API Key inválida.")
    return True

# -----------------------------------------------------------------------------
# Rate Limit
# -----------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="ImperadorVIP - Asset & AI Analysis API")
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS (abra para seu front/app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # troque para seu domínio quando tiver
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Banco (SQLAlchemy)
# -----------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

class Platform(StrEnum):
    deriv = "deriv"
    quotex = "quotex"
    iq = "iq"

class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(20), index=True)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[Optional[str]] = mapped_column(String(128), default=None)
    is_active: Mapped[int] = mapped_column(Integer, default=1)  # 1 true / 0 false
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("platform", "symbol", name="uq_platform_symbol"),
        Index("idx_assets_platform_symbol", "platform", "symbol"),
    )

class Candle(Base):
    __tablename__ = "candles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(20), index=True)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float, default=0.0)

    __table_args__ = (
        UniqueConstraint("platform", "symbol", "ts", name="uq_candle_unique"),
        Index("idx_candles_plat_sym_ts", "platform", "symbol", "ts"),
    )

class Signal(Base):
    __tablename__ = "signals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(20), index=True)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True)
    rsi: Mapped[Optional[float]] = mapped_column(Float, default=None)
    sma_fast: Mapped[Optional[float]] = mapped_column(Float, default=None)
    sma_slow: Mapped[Optional[float]] = mapped_column(Float, default=None)
    trend: Mapped[Optional[str]] = mapped_column(String(16), default=None)
    confluence: Mapped[Optional[str]] = mapped_column(String(16), default=None)  # buy/sell/neutral

    __table_args__ = (
        Index("idx_signals_plat_sym_ts", "platform", "symbol", "ts"),
    )

Base.metadata.create_all(engine)

# -----------------------------------------------------------------------------
# Modelos (Pydantic)
# -----------------------------------------------------------------------------
class AssetOut(BaseModel):
    platform: Platform
    symbol: str
    name: Optional[str] = None
    is_active: bool = True

class SyncAssetsIn(BaseModel):
    platforms: Optional[List[Platform]] = Field(default=None, description="Se vazio: sincroniza todas")

class CandleIn(BaseModel):
    platform: Platform
    symbol: str
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

class AnalysisOut(BaseModel):
    platform: Platform
    symbol: str
    lookback: int
    last_ts: Optional[datetime]
    indicators: Dict[str, Any]
    signal: Optional[str]

# -----------------------------------------------------------------------------
# Seeds estáticos de ATIVOS (ponto de partida)
# -----------------------------------------------------------------------------
STATIC_ASSETS = {
    "deriv": [
        # Synthetic + crypto/forex (exemplos; adicione o que quiser)
        "BOOM1000","CRASH1000","BOOM500","CRASH500","BOOM300","CRASH300",
        "BOOM600","CRASH600","BOOM900","CRASH900",
        "cryBTCUSD","cryETHUSD","EURUSD","GBPUSD","USDJPY"
    ],
    "quotex": [
        "EURUSD","GBPUSD","USDJPY","AUDCAD","BTCUSD","ETHUSD"
    ],
    "iq": [
        "EURUSD","GBPUSD","USDJPY","AUDCAD","AUDUSD","BTCUSD","ETHUSD"
    ],
}

# -----------------------------------------------------------------------------
# Funções de sincronização de ATIVOS
# (no modo 'static' usa seeds; depois podemos implementar 'live')
# -----------------------------------------------------------------------------
async def fetch_assets_deriv_live() -> List[str]:
    # TODO: implementar via API oficial da Deriv (active_symbols)
    # Por ora, retorna seed até conectarmos live.
    return STATIC_ASSETS["deriv"]

async def fetch_assets_quotex_live() -> List[str]:
    # TODO: implementar quando API pública estável estiver definida
    return STATIC_ASSETS["quotex"]

async def fetch_assets_iq_live() -> List[str]:
    # TODO: IQ tem SDKs não-oficiais; manter seed por enquanto
    return STATIC_ASSETS["iq"]

async def get_assets_for_platform(platform: Platform) -> List[str]:
    if ASSET_SYNC_MODE == "live":
        if platform == Platform.deriv:
            return await fetch_assets_deriv_live()
        if platform == Platform.quotex:
            return await fetch_assets_quotex_live()
        if platform == Platform.iq:
            return await fetch_assets_iq_live()
    # default: static
    return STATIC_ASSETS[platform.value]

def upsert_assets(db: Session, platform: Platform, symbols: List[str]) -> int:
    inserted = 0
    for sym in symbols:
        # UPSERT simples
        exists = db.execute(
            text("SELECT id FROM assets WHERE platform=:p AND symbol=:s"),
            {"p": platform.value, "s": sym}
        ).first()
        if exists is None:
            db.execute(
                text("""INSERT INTO assets (platform, symbol, name, is_active, created_at)
                        VALUES (:p, :s, :n, :ia, :ca)"""),
                {"p": platform.value, "s": sym, "n": sym, "ia": 1, "ca": datetime.utcnow()}
            )
            inserted += 1
    db.commit()
    return inserted

# -----------------------------------------------------------------------------
# Ingestão de CANDLES (seu feed publica aqui)
# -----------------------------------------------------------------------------
@app.post("/ingest/candle")
@limiter.limit("120/minute")
def ingest_candle(payload: CandleIn, ok: bool = Depends(require_api_key)):
    with Session(engine) as db:
        # UPSERT por (platform,symbol,ts)
        db.execute(
            text("""INSERT INTO candles (platform, symbol, ts, open, high, low, close, volume)
                    VALUES (:p,:s,:ts,:o,:h,:l,:c,:v)
                    ON CONFLICT (platform, symbol, ts) DO UPDATE
                    SET open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
                        close=EXCLUDED.close, volume=EXCLUDED.volume
            """),
            {"p":payload.platform.value,"s":payload.symbol,"ts":payload.ts,
             "o":payload.open,"h":payload.high,"l":payload.low,"c":payload.close,"v":payload.volume}
        )
        db.commit()
    return {"status":"ok"}

# Ingestão em lote
@app.post("/ingest/candles")
@limiter.limit("60/minute")
def ingest_candles(
    items: List[CandleIn],
    ok: bool = Depends(require_api_key)
):
    with Session(engine) as db:
        for c in items:
            db.execute(
                text("""INSERT INTO candles (platform, symbol, ts, open, high, low, close, volume)
                        VALUES (:p,:s,:ts,:o,:h,:l,:c,:v)
                        ON CONFLICT (platform, symbol, ts) DO UPDATE
                        SET open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
                            close=EXCLUDED.close, volume=EXCLUDED.volume
                """),
                {"p":c.platform.value,"s":c.symbol,"ts":c.ts,
                 "o":c.open,"h":c.high,"l":c.low,"c":c.close,"v":c.volume}
            )
        db.commit()
    return {"status":"ok","count":len(items)}

# -----------------------------------------------------------------------------
# Sincronização de ATIVOS
# -----------------------------------------------------------------------------
@app.post("/assets/sync")
@limiter.limit("20/minute")
async def sync_assets(body: SyncAssetsIn = Body(default=SyncAssetsIn()), ok: bool = Depends(require_api_key)):
    platforms = body.platforms or [Platform.deriv, Platform.quotex, Platform.iq]
    summary = {}
    with Session(engine) as db:
        for p in platforms:
            symbols = await get_assets_for_platform(p)
            inserted = upsert_assets(db, p, symbols)
            summary[p.value] = {"found": len(symbols), "inserted": inserted}
    return {"mode": ASSET_SYNC_MODE, "summary": summary}

# Listagem de ATIVOS (com filtros)
@app.get("/assets", response_model=List[AssetOut])
@limiter.limit("60/minute")
def list_assets(
    platform: Optional[Platform] = Query(default=None),
    search: Optional[str] = Query(default=None),
):
    q = "SELECT platform, symbol, name, is_active FROM assets"
    conds = []
    params = {}
    if platform:
        conds.append("platform=:p")
        params["p"] = platform.value
    if search:
        conds.append("(symbol ILIKE :q OR name ILIKE :q)")
        params["q"] = f"%{search}%"
    if conds:
        q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY platform, symbol LIMIT 2000"
    with Session(engine) as db:
        rows = db.execute(text(q), params).all()
    return [
        AssetOut(
            platform=row[0], symbol=row[1], name=row[2],
            is_active=bool(row[3])
        ) for row in rows
    ]

# -----------------------------------------------------------------------------
# Análise de GRÁFICO com IA (indicadores + confluência)
# -----------------------------------------------------------------------------
def make_analysis(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Espera df com colunas: ['ts','open','high','low','close','volume']
    Retorna indicadores e sinal agregado.
    """
    df = df.sort_values("ts").reset_index(drop=True)

    # Indicadores
    close = df["close"]
    rsi = RSIIndicator(close=close, window=14).rsi()
    sma_fast = SMAIndicator(close=close, window=9).sma_indicator()
    sma_slow = SMAIndicator(close=close, window=21).sma_indicator()

    # Tendência simples
    trend = "up" if sma_fast.iloc[-1] > sma_slow.iloc[-1] else "down"

    # Regras de confluência (exemplo simples e conservador)
    last_rsi = float(rsi.iloc[-1])
    last_fast = float(sma_fast.iloc[-1])
    last_slow = float(sma_slow.iloc[-1])
    last_close = float(close.iloc[-1])

    signal = "neutral"
    score = 0

    # RSI zonas
    if last_rsi < 30: score += 1
    if last_rsi > 70: score -= 1

    # Cruzamento e posição MAs
    if last_fast > last_slow and last_close > last_fast: score += 1
    if last_fast < last_slow and last_close < last_fast: score -= 1

    # Resultado final
    if score >= 2:
        signal = "buy"
    elif score <= -2:
        signal = "sell"
    else:
        signal = "neutral"

    return {
        "rsi": round(last_rsi, 2),
        "sma_fast": round(last_fast, 5),
        "sma_slow": round(last_slow, 5),
        "trend": trend,
        "score": score,
        "last_close": last_close,
    }, signal

@app.get("/chart/{platform}/{symbol}", response_model=AnalysisOut)
@limiter.limit("60/minute")
def analyze_chart(
    platform: Platform,
    symbol: str,
    lookback: int = Query(default=200, ge=30, le=2000),
    ok: bool = Depends(require_api_key)
):
    with Session(engine) as db:
        rows = db.execute(
            text("""SELECT ts, open, high, low, close, volume
                    FROM candles
                    WHERE platform=:p AND symbol=:s
                    ORDER BY ts DESC
                    LIMIT :lb"""),
            {"p": platform.value, "s": symbol, "lb": lookback}
        ).all()

    if not rows:
        raise HTTPException(status_code=204, detail="Sem candles para este ativo.")

    df = pd.DataFrame(rows, columns=["ts","open","high","low","close","volume"])
    indicators, final_signal = make_analysis(df)

    # (Opcional) persistir último sinal
    with Session(engine) as db:
        db.add(Signal(
            platform=platform.value, symbol=symbol,
            ts=df["ts"].iloc[-1],
            rsi=indicators["rsi"],
            sma_fast=indicators["sma_fast"],
            sma_slow=indicators["sma_slow"],
            trend=indicators["trend"],
            confluence=final_signal
        ))
        db.commit()

    return AnalysisOut(
        platform=platform,
        symbol=symbol,
        lookback=lookback,
        last_ts=df["ts"].iloc[-1],
        indicators=indicators,
        signal=final_signal
    )

# -----------------------------------------------------------------------------
# Health & raiz
# -----------------------------------------------------------------------------
@app.get("/")
def root():
    return {
        "app": "ImperadorVIP - Assets & AI",
        "db": "ok",
        "asset_sync_mode": ASSET_SYNC_MODE,
        "docs": ["/docs", "/redoc"]
    }

@app.get("/health")
def health():
    # ping simples
    with engine.connect() as c:
        c.execute(text("SELECT 1"))
    return {"status": "ok"}

# -----------------------------------------------------------------------------
# Startup: sincroniza assets (estático por padrão)
# -----------------------------------------------------------------------------
@app.on_event("startup")
async def startup():
    # Sincroniza todas as corretoras na inicialização
    with Session(engine) as db:
        for p in [Platform.deriv, Platform.quotex, Platform.iq]:
            symbols = await get_assets_for_platform(p)
            upsert_assets(db, p, symbols)
