from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests, os, time, threading
from dotenv import load_dotenv
import random

# Carregar variáveis .env
load_dotenv()

app = FastAPI(title="IA do Imperador - Live Signals")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================
# Configurações e variáveis
# =============================
TWELVEDATA_KEY = os.getenv("TWELVEDATA_API_KEY")
BASE_URL = "https://api.twelvedata.com/time_series"
LIVE_SIGNAL = {"status": "aguardando", "sinal": None, "confiança": 0, "par": None, "horario": None}

# =============================
# Função: análise de confluência
# =============================
def gerar_analise_simples(symbol="EUR/USD"):
    try:
        params = {
            "symbol": symbol,
            "interval": "1min",
            "outputsize": 5,
            "apikey": TWELVEDATA_KEY
        }
        r = requests.get(BASE_URL, params=params, timeout=10)
        data = r.json()

        if "values" not in data:
            raise Exception(data.get("message", "Erro desconhecido"))

        # Simplificação — usa última vela
        valores = data["values"]
        ultima = float(valores[0]["close"])
        penultima = float(valores[1]["close"])

        # Exemplo básico de lógica direcional
        direcao = "CALL" if ultima > penultima else "PUT"
        confianca = random.randint(85, 99)  # Simulação (substituir por IA real depois)

        return {
            "symbol": symbol,
            "sinal": direcao,
            "confianca": confianca,
            "ultimo_preco": ultima,
            "penultimo": penultima,
            "status": "ok"
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Falha ao consultar TwelveData: {e}")

# =============================
# Rota 1 — Teste de conexão
# =============================
@app.get("/")
def root():
    return {"status": "online", "mensagem": "Servidor ativo da IA do Imperador"}

# =============================
# Rota 2 — Sinal manual
# =============================
@app.post("/signal/test")
def test_signal():
    result = gerar_analise_simples()
    return result

# =============================
# Rota 3 — Sinal ao vivo (a cada 60s)
# =============================
@app.get("/signal/live")
def live_signal():
    global LIVE_SIGNAL
    return LIVE_SIGNAL

def atualizar_sinal_automatico():
    global LIVE_SIGNAL
    while True:
        try:
            sinal = gerar_analise_simples("EUR/USD")
            if sinal["confianca"] >= 90:
                LIVE_SIGNAL.update({
                    "status": "ativo",
                    "sinal": sinal["sinal"],
                    "confiança": sinal["confianca"],
                    "par": sinal["symbol"],
                    "horario": time.strftime("%H:%M:%S")
                })
                print(f"[{LIVE_SIGNAL['horario']}] Sinal emitido: {LIVE_SIGNAL}")
            else:
                LIVE_SIGNAL.update({
                    "status": "aguardando",
                    "sinal": None,
                    "confiança": sinal["confianca"],
                    "par": sinal["symbol"],
                    "horario": time.strftime("%H:%M:%S")
                })
        except Exception as e:
            LIVE_SIGNAL["status"] = f"erro: {e}"

        time.sleep(60)  # intervalo de 60 segundos

# Iniciar thread automática
threading.Thread(target=atualizar_sinal_automatico, daemon=True).start()
