
# ImperadorVIP API (Base44 + Railway)

## Deploy Rápido
1. Suba **esta pasta completa** no GitHub (nome do repo à sua escolha).
2. No Railway, crie um serviço via GitHub e conecte esse repo.
3. Em **Variables**, adicione (se ainda não aparecerem):
   - `PORT=8080`
   - `API_KEY=imperadorvip-secure-key-2025`
   - `TWELVEDATA_KEY=aa65a6636b6f48c2a7970e02611b25f0`
4. Deploy. Healthcheck: `/health`.

## Rotas
- `GET /health`
- `GET /signals/config`
- `POST /signals/manual`
- `POST /signals/auto`
