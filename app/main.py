from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from routes.signal_routes import router as signal_router
from routes.health_routes import router as health_router
import os

app = FastAPI(title="ImperadorVIP Signals API", version="4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(signal_router, prefix="/signal", tags=["Signals"])
app.include_router(health_router, prefix="/health", tags=["Health"])

@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "ImperadorVIP Signals API",
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
