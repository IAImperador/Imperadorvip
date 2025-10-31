import httpx, os, random

async def obter_sinal():
    ativos = ["EUR/USD", "USD/JPY", "GBP/USD", "AUD/USD", "USD/CHF", "NZD/USD"]
    ativo = random.choice(ativos)
    confianca = round(random.uniform(88, 99), 2)
    direcao = "CALL" if confianca > 92 else "PUT"
    return {"ativo": ativo, "sinal": direcao, "confianca": confianca}
