from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio, httpx, os, json, datetime, random

app = FastAPI(title="IA do Imperador - Live Signals")

# ============= CORS LIBERADO =============
origins = [
    "https://imperadorvip-production.up.railway.app",
    "https://imperadorvip.base44.app",
    "https://app.base44.io",
    "*"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= VARIÁVEIS .ENV =============
API_KEY = os.getenv

