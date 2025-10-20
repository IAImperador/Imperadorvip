import os
import json
import time
import random
import logging
import asyncio
from typing import Dict, Any, Optional, Callable, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

# -----------------------------
# Config & Helpers
# -----------------------------
APP_NAME = os.getenv("APP_NAME", "ImperadorVIP")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
API_KEY = os.getenv("API_KEY", "imperador_secret_key")
ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",")
] if os.getenv("ALLOWED_ORIGINS") else ["*"]

REFRESH_INTERVAL = float(os.getenv("REFRESH_INTERVAL", "5"))
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "15"))

PORT = int(os.getenv("PORT", os.getenv("RAILWAY_STATIC_PORT", "8080")))

# Banco é opcional para rodar; se quiser usar, injete DATABASE_URL no Railway
DATABASE_URL = os.getenv("DATABASE_URL")

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("imperadorvip")

# -----------------------------
# Catálogo de Corretoras
# -----------------------------
# Nome interno     : (rótulo, env_enable, cred_vars)
BROKERS: Dict[str, Dict[str, Any]] = {
    "deriv":      {"label": "Deriv",       "enable": "ENABLE_DERIV",      "creds": ["TOKEN_DERIV"]},
    "quotex":     {"label": "Quotex",      "enable": "ENABLE_QUOTEX",     "creds": ["QUOTEX_EMAIL", "QUOTEX_SENHA"]},
    "iqoption":   {"label": "IQ Option",   "enable": "ENABLE_IQOPTION",   "creds": ["IQ_EMAIL", "IQ_SENHA"]},
    "avalon":     {"label": "Avalon",      "enable": "ENABLE_AVALON",     "creds": ["AVALON_EMAIL", "AVALON_SENHA"]},
    "bullex":     {"label": "Bullex",      "enable": "ENABLE_BULLEX",     "creds": ["BULLEX_EMAIL", "BULLEX_SENHA"]},
    "casatrader": {"label": "CasaTrader",  "enable": "ENABLE_CASATRADER", "creds": ["CASATRADER_EMAIL", "CASATRADER_SENHA"]},
    "nexbroker":  {"label": "NexBroker",   "enable": "ENABLE_NEXBROKER",  "creds": ["NEXBROKER_EMAIL", "NEXBROKER_SENHA"]},
    "polarium":   {"label": "Polarium",    "enable": "ENABLE_POLARIUM",   "creds": ["POLARIUM_E_MAIL", "POLARIUM_SENHA"]},
    "corretor10": {"label": "Corretor10",  "enable": "ENABLE_CORRETOR10", "creds": ["CORRETOR10_E_MAIL", "CORRETOR10_SENHA"]},
}

def _env_true(name: str) -> bool:
    v = os.getenv(name)
    return bool(v) and v.lower() in {"1", "true", "yes", "on"}

def _has_all_creds(keys: List[str]) -> bool:
    return all(os.getenv(k) not in (None, "") for k in keys)

def enabled_brokers() -> Dict[str, Dict[str, Any]]:
    """Retorna apenas as corretoras habilitadas por env ENABLE_* (ou por presença de credenciais)."""
    active = {}
    for code, meta in BROKERS.items():
        enabled_flag = _env_true(meta["enable"])
        has_creds = _has_all_creds(meta["creds"])
        if enabled_flag or has_creds:
            active[code] = {
                "code": code,
                "label": meta["label"],
                "enabled_by": "flag" if enabled_flag else "creds",
                "creds_required": meta["creds"],
                "creds_present": has_creds,
            }
    return active

# -----------------------------
# Autenticação simples por header
# -----------------------------
def require_api_key(x_api_key: Optional[str]) -> None:
    if not API_KEY:
        # Sem exigência
        return
    if x_api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

async def api_key_dep(x_api_key: Optional[str] = None):
    # FastAPI injeta headers por nome do parâmetro; no WS faremos check manual
    require_api_key(x_api_key)

# -----------------------------
# Conectores (placeholders)
# -----------------------------
class BaseConnector:
    def __init__(self, code: str, label: str):
        self.code = code
        self.label = label
        self._running = False

    async def login(self) -> None:
        # Aqui você implementa o login real da corretora
        await asyncio.sleep(0.1)

    async def _connect_and_stream(self, ws_send: Callable[[Dict[str, Any]], asyncio.Future]) -> None:
        """
        Substitua este método pelo stream oficial da corretora.
        Por enquanto, envia ticks + 'sinais' simulados para a Base44.
        """
        self._running = True
        last_price = 100.0 + random.random()
        while self._running:
            # Simula preço
            delta = random.uniform(-0.25, 0.25)
            last_price = max(0.01, last_price + delta)

            # Simula padrões/estratégias (gatilhos básicos)
            pattern = random.choice([
                "retração", "rompimento", "lta", "ltb",
                "canal_alta", "canal_baixa", "limite_preco",
                "primeiro_registro", "martelo", "engolfo",
            ])
            signal = {
                "t": int(time.time() * 1000),
                "broker": self.code,
                "price": round(last_price, 5),
                "pattern": pattern,
                "confidence": round(random.uniform(0.55, 0.92), 2),
            }
            await ws_send({"type": "tick", "data": signal})

            # A cada N ticks, manda um “setup” de entrada
            if random.random() > 0.85:
                setup = {
                    "symbol": random.choice(["EURUSD", "USDJPY", "BTCUSD", "XAUUSD"]),
                    "timeframe": random.choice(["M1", "M5", "M15"]),
                    "strategy": random.choice(["retração", "rompimento", "pullback", "breakout"]),
                    "direction": random.choice(["CALL", "PUT"]),
                    "sl": round(last_price - random.uniform(0.2, 0.6), 5),
                    "tp": round(last_price + random.uniform(0.2, 0.6), 5),
                }
                await ws_send({"type": "setup", "data": setup})

            await asyncio.sleep(max(0.2, REFRESH_INTERVAL / 5.0))

    async def stop(self) -> None:
        self._running = False

# Cria uma fábrica para cada corretora (mantemos a mesma classe-base; troque por classes específicas se quiser)
def make_connector(broker_code: str) -> BaseConnector:
    label = BROKERS[broker_code]["label"]
    return BaseConnector(broker_code, label)

# -----------------------------
# App & Lifespan
# -----------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting %s ...", APP_NAME)
    # Aqui você poderia abrir pool do banco (se DATABASE_URL estiver setado)
    yield
    log.info("Shutting down %s ...", APP_NAME)

app = FastAPI(title=APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Rotas HTTP
# -----------------------------
@app.get("/")
async def root():
    return {
        "status": "online",
        "app": APP_NAME,
        "brokers_enabled": list(enabled_brokers().keys()),
        "message": "IA ImperadorVIP ativa e rodando com sucesso.",
    }

@app.get("/health")
async def health():
    return {"ok": True, "ts": int(time.time())}

@app.get("/brokers", dependencies=[Depends(api_key_dep)])
async def list_brokers():
    return enabled_brokers()

# -----------------------------
# WebSocket por corretora
# -----------------------------
# Um “hub” simples de clientes conectados por corretora
CLIENTS: Dict[str, List[WebSocket]] = {code: [] for code in BROKERS.keys()}

async def _send_json(ws: WebSocket, payload: Dict[str, Any]) -> None:
    try:
        await ws.send_text(json.dumps(payload, ensure_ascii=False))
    except Exception as e:
        log.warning("Send failed: %s", e)

@app.websocket("/ws/{broker}/{user_id}")
async def ws_broker(websocket: WebSocket, broker: str, user_id: str):
    # Autenticação por header
    client_key = websocket.headers.get("x-api-key")
    try:
        require_api_key(client_key)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    broker = broker.lower()
    active = enabled_brokers()
    if broker not in active:
        await websocket.accept()
        await _send_json(websocket, {"type": "error", "message": f"Broker '{broker}' não habilitado"})
        await websocket.close()
        return

    await websocket.accept()
    CLIENTS.setdefault(broker, []).append(websocket)

    connector = make_connector(broker)

    async def ws_send(payload: Dict[str, Any]):
        payload = {"user": user_id, **payload}
        await _send_json(websocket, payload)

    producer_task = asyncio.create_task(connector._connect_and_stream(ws_send))

    try:
        # Loop do consumidor: recebe mensagens do cliente (pings, comandos, etc.)
        while True:
            msg = await websocket.receive_text()
            # eco/ack
            await ws_send({"type": "ack", "echo": msg})
    except WebSocketDisconnect:
        pass
    finally:
        await connector.stop()
        producer_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await producer_task
        if websocket in CLIENTS.get(broker, []):
            CLIENTS[broker].remove(websocket)
