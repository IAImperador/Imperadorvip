# ImperadorVIP — Signals API (Base44/HTTP)

API para sinais com leitura por mercado (OTC/Aberto). Modo automático opcional (5 min).

## Endpoints
- GET /
- GET /status
- GET /signal/live?market=otc|aberto&symbol=EUR/USD
- POST /auto/toggle   (Header: X-API-Key)

## .env
PORT=8080
API_KEY=imperadorvip-secure-key-2025
TWELVEDATA_KEY=aa65a6636b6f48c2a7970e02611b25f0
ENVIRONMENT=production
DEBUG=false
