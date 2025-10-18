import os
import json
import time
import threading
from typing import Dict, Any, Optional
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel, Field

# -----------------------------
# App
# -----------------------------
app = FastAPI(title="ImperadorVIP - Global Signal Engine (Public + Auth)")

# -----------------------------
# Feeds públicos (Deriv)
# -----------------------------
from websocket import WebSocketApp  # pacote: websocket-client

DERIV_WS_URL = "wss://ws.binaryws.com/websockets/v3?app_id=1089"
DERIV_SYMBOLS = [
    # Synthetics + Crypto que você já estava usando
    "CRASH900", "BOOM1000", "CRASH1000", "BOOM600", "BOOM300N",
    "CRASH600", "RDBULL", "cryETHUSD", "CRASH500", "BOOM900",
    "cryBTCUSD", "CRASH300N", "RDBEAR", "BOOM500"
]

deriv_prices: Dict[str, Dict[str, Any]] = {}
_deriv_ws: Optional[WebSocketApp] = None
_deriv_connected = False


def _deriv_on_message(ws, message: str):
    try:
        data = json.loads(message)
        # tick stream response example: {"tick":{"symbol":"R_100","quote":123.45,"epoch":...}, "subscription": {...}}
        if "tick" in data and isinstance(data["tick"], dict):
            sym = data["tick"].get("symbol")
            quote = data["tick"].get("quote")
            epoch = data["tick"].get("epoch")
            if sym and quote is not None:
                deriv_prices[sym] = {"price": quote, "ts": epoch}
    except Exception as e:
        print(f"[DERIV on_message] {e}")


def _deriv_on_open(ws):
    global _deriv_connected
    _deriv_connected = True
    print("[DERIV] Connected.")
    # Subscribe each symbol to ticks
    subscribed = 0
    for s in DERIV_SYMBOLS:
        msg = {"ticks": s, "subscribe": 1}
        try:
            ws.send(json.dumps(msg))
            subscribed += 1
        except Exception as e:
            print(f"[DERIV] subscribe({s}) error: {e}")
    print(f"[DERIV] Subscribed to {subscribed} symbols.")


def _deriv_on_error(ws, error):
    print(f"[DERIV] Error: {error}")


def _deriv_on_close(ws, code, reason):
    global _deriv_connected
    _deriv_connected = False
    print(f"[DERIV] Closed ({code}): {reason}. Reconnecting in 5s...")
    time.sleep(5)
    start_deriv_thread()  # auto-reconnect


def start_deriv_thread():
    global _deriv_ws
    if _deriv_ws is not None:
        try:
            _deriv_ws.close()
        except Exception:
            pass
    _deriv_ws = WebSocketApp(
        DERIV_WS_URL,
        on_open=_deriv_on_open,
        on_message=_deriv_on_message,
        on_error=_deriv_on_error,
        on_close=_deriv_on_close,
    )
    t = threading.Thread(target=_deriv_ws.run_forever, kwargs={"ping_interval": 20}, daemon=True)
    t.start()


# -----------------------------
# Sessões autenticadas (Quotex / IQ)
# -----------------------------
class LoginPayload(BaseModel):
    user_id: str = Field(..., description="ID único do seu cliente (ex: email, UUID etc.)")
    email: str = Field(..., description="Email do cliente na corretora")
    password: str = Field(..., description="Senha do cliente na corretora")


class DisconnectPayload(BaseModel):
    user_id: str
    platform: str  # "quotex" ou "iq"


# Guardamos apenas estado serializável separadamente;
# objetos de conexão ficam em mapas internos (não retornados via API).
sessions_state: Dict[str, Dict[str, Dict[str, Any]]] = {
    "quotex": {},  # user_id -> {connected: bool, last_error: str|None, since: ts}
    "iq": {},      # idem
}
# Armazena objetos vivos (não serializar)
_quotex_clients: Dict[str, Any] = {}
_iq_clients: Dict[str, Any] = {}

_quotex_lock = threading.Lock()
_iq_lock = threading.Lock()


def _set_state(platform: str, user_id: str, connected: bool, last_error: Optional[str] = None):
    sessions_state.setdefault(platform, {}).setdefault(user_id, {})
    sessions_state[platform][user_id]["connected"] = connected
    sessions_state[platform][user_id]["since"] = int(time.time())
    sessions_state[platform][user_id]["last_error"] = last_error


def _connect_quotex_thread(user_id: str, email: str, password: str):
    """
    Tenta conectar Quotex para este user_id em thread separada.
    Requer pacote: quotexapi (não-oficial).
    """
    try:
        from quotexapi.stable_api import Quotex  # pip install quotexapi
    except Exception as e:
        _set_state("quotex", user_id, False, f"Pacote quotexapi indisponível: {e}")
        return

    try:
        # Fecha sessão anterior deste user, se houver
        with _quotex_lock:
            old = _quotex_clients.pop(user_id, None)
            if old:
                try:
                    old.close()
                except Exception:
                    pass

        client = Quotex(email, password)
        ok = client.connect()
        if not ok:
            _set_state("quotex", user_id, False, "Falha de autenticação ou bloqueio regional")
            return

        # Se conectou, guarda referência
        with _quotex_lock:
            _quotex_clients[user_id] = client
        _set_state("quotex", user_id, True, None)

        # (Opcional) Assinaturas de preços/velas específicas por usuário
        # Ex.: client.subscribe_realtime("EURUSD", period=60)
        # Mantém a thread viva checando conexão
        while True:
            time.sleep(20)
            # Aqui você pode checar um ping, saldo, etc.
            # Se cair, marque desconectado e break
            # (muitos wrappers não expõem 'is_connected'; trate exceções)
    except Exception as e:
        _set_state("quotex", user_id, False, str(e))


def _connect_iq_thread(user_id: str, email: str, password: str):
    """
    Tenta conectar IQ Option para este user_id em thread separada.
    Requer pacote: iqoptionapi (não-oficial).
    """
    try:
        from iqoptionapi.stable_api import IQ_Option  # pip install iqoptionapi
    except Exception as e:
        _set_state("iq", user_id, False, f"Pacote iqoptionapi indisponível: {e}")
        return

    try:
        with _iq_lock:
            old = _iq_clients.pop(user_id, None)
            if old:
                try:
                    old.close()
                except Exception:
                    pass

        Iq = IQ_Option(email, password)
        connected, reason = Iq.connect()
        if not connected:
            _set_state("iq", user_id, False, f"Falha de autenticação: {reason}")
            return

        with _iq_lock:
            _iq_clients[user_id] = Iq
        _set_state("iq", user_id, True, None)

        # Você pode ativar assinaturas de velas:
        # Iq.start_candles_stream("EURUSD", 60, 100)
        while True:
            time.sleep(20)
            # Opcional: verificar algo do socket; se falhar, marcar como desconectado
    except Exception as e:
        _set_state("iq", user_id, False, str(e))


def _disconnect_user(platform: str, user_id: str):
    if platform == "quotex":
        with _quotex_lock:
            client = _quotex_clients.pop(user_id, None)
            if client:
                try:
                    client.close()
                except Exception:
                    pass
        _set_state("quotex", user_id, False, None)
        return True

    if platform == "iq":
        with _iq_lock:
            client = _iq_clients.pop(user_id, None)
            if client:
                try:
                    client.close()
                except Exception:
                    pass
        _set_state("iq", user_id, False, None)
        return True

    return False


# -----------------------------
# Endpoints públicos
# -----------------------------
@app.get("/")
def root():
    return {
        "app": "ImperadorVIP - Global Signal Engine (Public + Auth)",
        "auto_mode": False,
        "feeds": {
            "deriv_connected": _deriv_connected,
            "quotex_connected": any(v.get("connected") for v in sessions_state.get("quotex", {}).values()),
            "iq_connected": any(v.get("connected") for v in sessions_state.get("iq", {}).values()),
        },
        "symbols_tracked": list(deriv_prices.keys())[:200],
    }


@app.get("/health")
def health():
    return {"status": "ok", "ts": int(time.time())}


@app.get("/feeds/deriv/price/{symbol}")
def deriv_price(symbol: str):
    sym = symbol.upper()
    d = deriv_prices.get(sym)
    if not d:
        return {"error": f"no recent price for {sym}"}
    return {"symbol": sym, "price": d["price"], "ts": d["ts"]}


@app.get("/sessions")
def sessions():
    # NÃO expõe objetos de conexão; apenas estado serializável
    return sessions_state


@app.post("/connect/quotex")
def connect_quotex(body: LoginPayload, tasks: BackgroundTasks):
    """
    Dispara conexão Quotex para este user_id (multiusuário).
    NÃO armazena senha; usa apenas para abrir a sessão.
    """
    _set_state("quotex", body.user_id, False, "connecting")
    tasks.add_task(_connect_quotex_thread, body.user_id, body.email, body.password)
    return {"ok": True, "platform": "quotex", "user_id": body.user_id, "message": "connecting"}


@app.post("/connect/iq")
def connect_iq(body: LoginPayload, tasks: BackgroundTasks):
    """
    Dispara conexão IQ Option para este user_id (multiusuário).
    """
    _set_state("iq", body.user_id, False, "connecting")
    tasks.add_task(_connect_iq_thread, body.user_id, body.email, body.password)
    return {"ok": True, "platform": "iq", "user_id": body.user_id, "message": "connecting"}


@app.post("/disconnect")
def disconnect(body: DisconnectPayload):
    ok = _disconnect_user(body.platform.lower(), body.user_id)
    return {"ok": ok, "platform": body.platform.lower(), "user_id": body.user_id}


# -----------------------------
# Startup
# -----------------------------
@app.on_event("startup")
def _startup():
    print("🚀 Iniciando feeds...")
    start_deriv_thread()


# -----------------------------
# Exec local (Railway usa PORT)
# -----------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
