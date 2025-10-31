import requests, os

API_KEY = os.getenv("TWELVEDATA_KEY")

def obter_dados_twelvedata(ativo="EUR/USD", intervalo="1min"):
    url = f"https://api.twelvedata.com/time_series?symbol={ativo}&interval={intervalo}&apikey={API_KEY}"
    try:
        resposta = requests.get(url, timeout=12)
        data = resposta.json()
        if "values" in data:
            return data
        return None
    except Exception as e:
        print(f"Erro TwelveData: {e}")
        return None
