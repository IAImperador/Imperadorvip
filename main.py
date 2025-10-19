from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
import asyncio
import os

app = FastAPI(title="ImperadorVIP - Painel de Status")

templates = Jinja2Templates(directory="templates")

# Mock temporário (você pode ligar aos dados reais depois)
status_data = {
    "deriv_connected": True,
    "quotex_connected": False,
    "iq_connected": False,
    "symbols_tracked": [
        "CRASH900", "BOOM1000", "CRASH1000", "BOOM600", "BOOM300", 
        "CRASH600", "RDBULL", "cryETHUSD", "CRASH500", "BOOM900", 
        "cryBTCUSD", "CRASH300", "RDBEAR", "BOOM500"
    ]
}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Renderiza o painel visual"""
    return templates.TemplateResponse("index.html", {"request": request, "status": status_data})

@app.get("/status", response_class=JSONResponse)
async def get_status():
    """Endpoint para atualizações em tempo real"""
    return status_data

@app.get("/refresh")
async def refresh_data():
    """Simula atualização automática (pode ser conectado aos feeds reais)"""
    await asyncio.sleep(1)
    return {"message": "Status atualizado!"}
