# ImperadorVIP Signals API
FastAPI + TwelveData + Telegram. Pronto para Railway.
## Variáveis (Railway -> Variables)
- PORT=8080
- API_KEY (mesmo do Base44)
- TWELVEDATA_KEY
- TELEGRAM_BOT_TOKEN (opcional)
- TELEGRAM_CHAT_ID (opcional)
## Rodar local
pip install -r requisitos.txt
uvicorn app.main:app --reload --port 8080
