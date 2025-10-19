import os
import asyncio
import json
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

# ====== Banco (opcional/assíncrono) ======
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# ====== .env opcional local ======
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# =========================================================
# 🔐 Segurança por API Key (via header: X-API-Key)
# =========================================================
API_KEY = os.getenv("API_KEY", "").strip()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def require_api_key(x_api_key: Optional[str] = Depends(api_key_header)):
    if not API_KEY:
        # Se não tiver API_KEY definida, bloqueamos tudo em produção
        raise HTTPException(status_code=500, detail="API_KEY não configurada no ambiente.")
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API Key inválida.")
    return True

# =========================================================
# 🌐 CORS
# =========================================================
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS: List[str] = [o.strip() for o in allowed_origins_env.split(",") if o.strip()] or ["*"]

# =========================================================
# 🗄️ Banco de Dados (opcional)
# =========================================================
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
engine = None
AsyncSessionLocal = None
Base = declarative_base()

if DATABASE_URL:
    # Railway: postgresql+asyncpg://...
    engine = create_async_engine(DATABASE_URL, echo=False, future=True)
    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> Optional[AsyncSession]:
    if AsyncSessionLocal is None:
        return None
    async with AsyncSessionLocal() as session:
        yield session

# =========================================================
# 🧠 Modelos / DTOs
# =========================================================
class ConnectRequest(BaseModel):
    user_id: str = Field(..., description="Identificador único do usuário/sessão.")
    brokers: Optional[List[str]] = Field(default=None, description="Se vazio, ativa todas com credencial presente.")

class Signal(BaseModel):
    timestamp: float
    broker: str
    asset: str
    timeframe: str
    direction: str         # "CALL" | "PUT" | "BUY" | "SELL"
    confidence: float      # 0..1
    reason: str

# =========================================================
# ♻️ Utilidades
# =========================================================
def env_has(*keys: str) -> bool:
    """Retorna True se TODAS as variáveis existirem e não forem vazias."""
    for k in keys:
        v = os.getenv(k, "").strip()
        if not v:
            return False
    return True

def now() -> float:
    return time.time()

# =========================================================
# 📈 Núcleo de Análise Técnica (simplificado / extensível)
# =========================================================
@dataclass
class Candle:
    ts: float
    open: float
    high: float
    low: float
    close: float

class Analyzer:
    """Cole aqui/estenda regras como retração, LTA/LTB, canais, rompimento, etc."""
    def __init__(self, lookback: int = 50) -> None:
        self.lookback = lookback
        self.buffer: Dict[str, List[Candle]] = {}  # key = f"{broker}:{asset}:{tf}"

    def push_candle(self, broker: str, asset: str, tf: str, candle: Candle) -> Optional[Signal]:
        key = f"{broker}:{asset}:{tf}"
        buf = self.buffer.setdefault(key, [])
        buf.append(candle)
        if len(buf) > self.lookback:
            buf.pop(0)

        # ===== Exemplos de padrões simples (ponto de partida) =====
        # 1) Rompimento de máxima/mínima recentes
        if len(buf) >= 10:
            highs = [c.high for c in buf[-10:]]
            lows  = [c.low for c in buf[-10:]]
            if candle.close >= max(highs):
                return Signal(
                    timestamp=now(), broker=broker, asset=asset, timeframe=tf,
                    direction="BUY", confidence=0.62, reason="Rompimento de máxima (10)"
                )
            if candle.close <= min(lows):
                return Signal(
                    timestamp=now(), broker=broker, asset=asset, timeframe=tf,
                    direction="SELL", confidence=0.62, reason="Rompimento de mínima (10)"
                )

        # 2) Retração (pavio longo)
        body = abs(candle.close - candle.open)
        upper_wick = candle.high - max(candle.close, candle.open)
        lower_wick = min(candle.close, candle.open) - candle.low
        if body > 0:
            if upper_wick >= 2 * body:
                return Signal(timestamp=now(), broker=broker, asset=asset, timeframe=tf,
                              direction="SELL", confidence=0.58, reason="Retração (pavio superior)")
            if lower_wick >= 2 * body:
                return Signal(timestamp=now(), broker=broker, asset=asset, timeframe=tf,
                              direction="BUY", confidence=0.58, reason="Retração (pavio inferior)")

        # 3) LTA/LTB (muito simplificado – tendência de 5 candles)
        if len(buf) >= 5:
            closes = [c.close for c in buf[-5:]]
            if all(closes[i] < closes[i+1] for i in range(4)):
                return Signal(timestamp=now(), broker=broker, asset=asset, timeframe=tf,
                              direction="BUY", confidence=0.55, reason="Sequência de topos/fundos ascendentes (LTA)")
            if all(closes[i] > closes[i+1] for i in range(4)):
                return Signal(timestamp=now(), broker=broker, asset=asset, timeframe=tf,
                              direction="SELL", confidence=0.55, reason="Sequência de topos/fundos descendentes (LTB)")

        return None

analyzer = Analyzer()

# =========================================================
# 🔌 Camada de Conectores (um por corretora)
# =========================================================
class BrokerAdapter:
    name: str = "base"
    def __init__(self, creds: Dict[str, str]) -> None:
        self.creds = creds
        self.running = False
        self.task: Optional[asyncio.Task] = None

    def has_credentials(self) -> bool:
        """Retorna True se credenciais presentes/aptas para conectar."""
        return all(bool(v) for v in self.creds.values())

    async def connect_and_stream(self, send_signal):
        """
        IMPLEMENTE AQUI O CLIENTE OFICIAL/WebSocket/SDK de cada corretora.
        Esta função deve:
          - Conectar
          - Assinar ativos/timeframes
          - Para cada candle/negociação, chamar send_signal(broker, asset, tf, Candle(...))
        """
        # Placeholder seguro: não faz nada, mas mantém o loop vivo.
        while self.running:
            await asyncio.sleep(1)

    async def start(self, send_signal):
        if self.running:
            return
        self.running = True
        self.task = asyncio.create_task(self.connect_and_stream(send_signal))

    async def stop(self):
        self.running = False
        if self.task:
            with contextlib.suppress(asyncio.CancelledError):
                self.task.cancel()
                await asyncio.sleep(0)

import contextlib
import random

# ---- Exemplo com "demo mode" para testes sem SDK (set SIMULATE_STREAMS=true) ----
SIMULATE = os.getenv("SIMULATE_STREAMS", "false").lower() in ("1", "true", "yes")

class SimulatedBroker(BrokerAdapter):
    """Simula candles e sinais se SIMULATE_STREAMS=true (útil para testar UI/WS)."""
    assets = ["EURUSD", "GBPUSD", "USDJPY"]
    tfs = ["1m", "5m"]

    async def connect_and_stream(self, send_signal):
        prices: Dict[str, float] = {a: 1.0 + random.random() * 0.1 for a in self.assets}
        while self.running:
            await asyncio.sleep(1)
            for asset in self.assets:
                last = prices[asset]
                delta = random.uniform(-0.002, 0.002)
                new = max(0.0001, last + delta)
                prices[asset] = new
                o = last
                h = max(o, new) + random.uniform(0, 0.001)
                l = min(o, new) - random.uniform(0, 0.001)
                c = new
                candle = Candle(ts=now(), open=o, high=h, low=l, close=c)
                sig = analyzer.push_candle(self.name, asset, "1m", candle)
                if sig:
                    await send_signal(sig)

# ---- Registro de corretoras (adicione quantas quiser) ----
def make_registry() -> Dict[str, BrokerAdapter]:
    registry: Dict[str, BrokerAdapter] = {}

    # IQ Option
    iq_creds = {
        "email": os.getenv("IQ_EMAIL", "").strip(),
        "password": os.getenv("IQ_SENHA", "").strip(),
    }
    adapter_iq = SimulatedBroker(iq_creds) if SIMULATE else BrokerAdapter(iq_creds)
    adapter_iq.name = "iq"
    if adapter_iq.has_credentials() or SIMULATE:
        registry["iq"] = adapter_iq

    # Quotex
    qx_creds = {
        "email": os.getenv("QUOTEX_EMAIL", "").strip(),
        "password": os.getenv("QUOTEX_SENHA", "").strip(),
    }
    adapter_qx = SimulatedBroker(qx_creds) if SIMULATE else BrokerAdapter(qx_creds)
    adapter_qx.name = "quotex"
    if adapter_qx.has_credentials() or SIMULATE:
        registry["quotex"] = adapter_qx

    # Deriv (token)
    deriv_creds = {"token": os.getenv("TOKEN_DERIV", "").strip()}
    adapter_deriv = SimulatedBroker(deriv_creds) if SIMULATE else BrokerAdapter(deriv_creds)
    adapter_deriv.name = "deriv"
    if adapter_deriv.has_credentials() or SIMULATE:
        registry["deriv"] = adapter_deriv

    # Bullex
    bullex_creds = {"email": os.getenv("BULLEX_EMAIL", "").strip(),
                    "password": os.getenv("BULLEX_SENHA", "").strip()}
    adapter_bullex = SimulatedBroker(bullex_creds) if SIMULATE else BrokerAdapter(bullex_creds)
    adapter_bullex.name = "bullex"
    if adapter_bullex.has_credentials() or SIMULATE:
        registry["bullex"] = adapter_bullex

    # Avalon
    avalon_creds = {"email": os.getenv("AVALON_EMAIL", "").strip(),
                    "password": os.getenv("AVALON_SENHA", "").strip()}
    adapter_avalon = SimulatedBroker(avalon_creds) if SIMULATE else BrokerAdapter(avalon_creds)
    adapter_avalon.name = "avalon"
    if adapter_avalon.has_credentials() or SIMULATE:
        registry["avalon"] = adapter_avalon

    # CasaTrader
    casa_creds = {"email": os.getenv("CASATRADER_EMAIL", "").strip(),
                  "password": os.getenv("CASATRADER_SENHA", "").strip()}
    adapter_casa = SimulatedBroker(casa_creds) if SIMULATE else BrokerAdapter(casa_creds)
    adapter_casa.name = "casatrader"
    if adapter_casa.has_credentials() or SIMULATE:
        registry["casatrader"] = adapter_casa

    # NexBroker
    nex_creds = {"email": os.getenv("NEXBROKER_EMAIL", "").strip(),
                 "password": os.getenv("NEXBROKER_SENHA", "").strip()}
    adapter_nex = SimulatedBroker(nex_creds) if SIMULATE else BrokerAdapter(nex_creds)
    adapter_nex.name = "nexbroker"
    if adapter_nex.has_credentials() or SIMULATE:
        registry["nexbroker"] = adapter_nex

    # Polarium
    pol_creds = {"email": os.getenv("POLARIUM_E-MAIL", os.getenv("POLARIUM_EMAIL", "")).strip(),
                 "password": os.getenv("POLARIUM_SENHA", "").strip()}
    adapter_pol = SimulatedBroker(pol_creds) if SIMULATE else BrokerAdapter(pol_creds)
    adapter_pol.name = "polarium"
    if adapter_pol.has_credentials() or SIMULATE:
        registry["polarium"] = adapter_pol

    # Broker10 (apelido CORRETOR10)
    b10_creds = {"email": os.getenv("CORRETOR10_E-MAIL", os.getenv("CORRETOR10_EMAIL", "")).strip(),
                 "password": os.getenv("CORRETOR10_SENHA", "").strip()}
    adapter_b10 = SimulatedBroker(b10_creds) if SIMULATE else BrokerAdapter(b10_creds)
    adapter_b10.name = "broker10"
    if adapter_b10.has_credentials() or SIMULATE:
        registry["broker10"] = adapter_b10

    return registry

BROKERS: Dict[str, BrokerAdapter] = make_registry()

# =========================================================
# 🔊 Broadcast de sinais (WebSocket por usuário)
# =========================================================
class WSManager:
    def __init__(self) -> None:
        self.connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, user_id: str, ws: WebSocket):
        await ws.accept()
        self.connections.setdefault(user_id, []).append(ws)

    def disconnect(self, user_id: str, ws: WebSocket):
        if user_id in self.connections:
            with contextlib.suppress(ValueError):
                self.connections[user_id].remove(ws)
            if not self.connections[user_id]:
                del self.connections[user_id]

    async def send(self, user_id: str, payload: Dict[str, Any]):
        if user_id not in self.connections:
            return
        dead = []
        for ws in self.connections[user_id]:
            try:
                await ws.send_text(json.dumps(payload, ensure_ascii=False))
            except WebSocketDisconnect:
                dead.append(ws)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)

ws_manager = WSManager()

# =========================================================
# 🧵 Sessões por usuário (vários usuários simultâneos)
# =========================================================
class UserSession:
    def __init__(self, user_id: str, brokers: Dict[str, BrokerAdapter]) -> None:
        self.user_id = user_id
        # Clones independentes por usuário
        self.adapters: Dict[str, BrokerAdapter] = {}
        for k, v in brokers.items():
            clone = type(v)(v.creds)  # mesmo tipo, mesmas creds
            clone.name = v.name
            self.adapters[k] = clone
        self.tasks: List[asyncio.Task] = []
        self.running = False

    async def send_signal(self, sig: Signal):
        await ws_manager.send(self.user_id, sig.model_dump())

    async def start(self, names: Optional[List[str]] = None):
        if self.running:
            return
        self.running = True
        targets = names or list(self.adapters.keys())
        for name in targets:
            adapter = self.adapters.get(name)
            if not adapter:
                continue
            await adapter.start(self.send_signal)

    async def stop(self):
        self.running = False
        for adapter in self.adapters.values():
            await adapter.stop()

SESSIONS: Dict[str, UserSession] = {}

# =========================================================
# 🚀 FastAPI
# =========================================================
app = FastAPI(title="ImperadorVIP API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    print("🚀 API ImperadorVIP iniciando...")
    print(f"✔ Broke rs disponíveis (com credencial ou simulação): {list(BROKERS.keys())}")
    if engine:
        async with engine.begin() as conn:
            # Se tivesse Base.metadata.create_all(...) faríamos aqui.
            pass

@app.on_event("shutdown")
async def on_shutdown():
    print("🛑 Encerrando sessões...")
    for sess in list(SESSIONS.values()):
        await sess.stop()

@app.get("/", tags=["Status"])
async def root():
    return {"ok": True, "msg": "ImperadorVIP online", "brokers": list(BROKERS.keys())}

@app.get("/health", tags=["Status"])
async def health():
    return {
        "ok": True,
        "db": bool(engine),
        "brokers_configured": list(BROKERS.keys()),
        "simulate": SIMULATE,
    }

# ---- Gerenciar sessões/streams ----
@app.post("/connect", tags=["Streams"])
async def connect(req: ConnectRequest, _=Depends(require_api_key)):
    if not req.user_id.strip():
        raise HTTPException(400, "user_id obrigatório.")
    if req.user_id in SESSIONS:
        # Reinicia
        await SESSIONS[req.user_id].stop()
        SESSIONS.pop(req.user_id, None)

    if not BROKERS:
        raise HTTPException(400, "Nenhuma corretora disponível (verifique variáveis).")

    # Filtra corretoras pedidas
    selected = {}
    if req.brokers:
        for b in req.brokers:
            if b not in BROKERS:
                raise HTTPException(400, f"Corretora não disponível: {b}")
            selected[b] = BROKERS[b]
    else:
        selected = BROKERS

    sess = UserSession(req.user_id, selected)
    SESSIONS[req.user_id] = sess
    await sess.start(list(selected.keys()))
    return {"ok": True, "user_id": req.user_id, "brokers": list(selected.keys())}

@app.post("/disconnect", tags=["Streams"])
async def disconnect(user_id: str = Query(...), _=Depends(require_api_key)):
    sess = SESSIONS.get(user_id)
    if not sess:
        return {"ok": True, "msg": "Sessão já inexistente."}
    await sess.stop()
    SESSIONS.pop(user_id, None)
    return {"ok": True, "user_id": user_id, "stopped": True}

# ---- WebSocket para sinais por usuário ----
@app.websocket("/ws/{user_id}")
async def ws_signals(ws: WebSocket, user_id: str):
    await ws_manager.connect(user_id, ws)
    try:
        while True:
            # Mantém o socket vivo; cliente pode enviar pings/opções
            _ = await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(user_id, ws)
    except Exception:
        ws_manager.disconnect(user_id, ws)

# =========================================================
# 🔧 Como ligar SDK oficial depois (exemplo)
# =========================================================
# Abra a classe BrokerAdapter da corretora desejada e troque o método
# connect_and_stream(...) por uma implementação real:
#
#   async def connect_and_stream(self, send_signal):
#       client = SDK(...)  # usando self.creds
#       await client.connect()
#       await client.subscribe("EURUSD", "1m")
#       async for event in client.candles():
#           candle = Candle(ts=event.ts, open=event.o, high=event.h, low=event.l, close=event.c)
#           sig = analyzer.push_candle(self.name, event.asset, event.tf, candle)
#           if sig:
#               await send_signal(sig)
#
# Não há necessidade de mexer no restante da API: endpoints e WebSocket já funcionam.
# =========================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8080")), reload=True)
