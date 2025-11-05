# ImperadorVIP — API de Sinais (Base44 + Railway)

API FastAPI pronta para o Railway e integrada ao painel Base44.
- Leitura **Mercado Aberto** (TwelveData) e flag **OTC** (manual).
- Modo **manual** e **automático** (o automático é chamado pelo painel a cada 5 min).
- Confluências: EMA(9/21), RSI(14), MACD(12,26,9), Estocástico(14,3), Bandas de Bollinger(20,2), padrões de candles (Martelo, Engolfo).
- Sem bot Telegram nesta versão.
- CORS liberado (origins="*").

## Variáveis de Ambiente (Railway → Variables)
```
PORT=8080
API_KEY=imperadorvip-secure-key-2025
TWELVEDATA_KEY=aa65a6636b6f48c2a7970e02611b25f0
```

## Deploy no Railway
1. Suba este repositório no GitHub (raiz contendo `main.py`, `requirements.txt`, `Procfile`).
2. Crie um serviço no Railway via GitHub.
3. Em **Variables**, adicione as três variáveis acima.
4. Deploy.
5. Teste `GET /health` no domínio do Railway.

## Endpoints
- `GET /health` → status
- `GET /config` → parâmetros padrão do servidor
- `POST /sinal/manual` → gerar sinal com parâmetros fornecidos no corpo
- `POST /sinal/auto` → mesma lógica do manual; o painel chama este a cada 5 min

> **Autenticação:** enviar cabeçalho `x-api-key: {API_KEY}` em cada requisição.

## Observações
- A fonte de dados em **mercado aberto** é a TwelveData (forex, crypto, ações, índices).
- Para **OTC**, o app respeita a flag do painel, porém a leitura usa as mesmas candles de referência (substitua por sua fonte OTC real quando desejar).
- O cálculo de confiança é heurístico (0–1) baseado na soma ponderada das confluências.
