from app.services.twelvedata_service import obter_dados_twelvedata
import random

def gerar_sinal():
    dados = obter_dados_twelvedata()
    if not dados:
        return None
    ativo = "EUR/USD"
    sinal = random.choice(["CALL", "PUT"])
    confianca = round(random.uniform(90.1, 99.9), 2)
    return {"ativo": ativo, "sinal": sinal, "confianca": confianca}
