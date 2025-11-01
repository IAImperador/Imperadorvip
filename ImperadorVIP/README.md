# ImperadorVIP — Railway + Base44 (sem Telegram)
Endpoints principais:
- `GET /health`
- `POST /signal/live` (com header `x-api-key`)

Exemplo de chamada:
```
POST /signal/live
x-api-key: imperadorvip-secure-key-2025
{
  "broker":"IQOption",
  "symbol":"EUR/USD",
  "timeframe":"5",
  "market_mode":"open",
  "manual": true
}
```
