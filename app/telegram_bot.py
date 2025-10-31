import os, httpx

async def enviar_telegram(mensagem: str):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return {"error": "Bot não configurado"}

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": mensagem, "parse_mode": "Markdown"}
    async with httpx.AsyncClient() as client:
        await client.post(url, data=data)
