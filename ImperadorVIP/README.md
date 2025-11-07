# ImperadorVIP – Sinais Inteligentes

Backend em FastAPI + UI simples.

## .env
Copie `.env.example` para `.env` e preencha:
```
PORT=8080
API_KEY=imperadorvip-secure-key-2025
TWELVEDATA_KEY=aa65a6636b6f48c2a7970e02611b25f0
ENVIRONMENT=production
DEBUG=false
```

## Local
```
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```
Abrir `web/index.html` e usar a URL `http://localhost:8080`.
