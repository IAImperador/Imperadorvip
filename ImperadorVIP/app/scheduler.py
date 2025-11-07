from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone
from .state import state
from .signals import generate_signal_once

scheduler = AsyncIOScheduler()

async def job_auto_signal():
    symbol = state.last_signal.get("symbol","EUR/USD")
    timeframe = state.last_signal.get("timeframe","5min")
    await generate_signal_once(symbol=symbol, timeframe=timeframe, min_confidence=90)

def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(job_auto_signal, "interval", minutes=5, next_run_time=datetime.now(timezone.utc))
        scheduler.start()
