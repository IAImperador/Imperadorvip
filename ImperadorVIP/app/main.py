from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title="ImperadorVIP", version="1.0")

# CORS - MUITO IMPORTANTE!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "status": "online",
        "app": "ImperadorVIP IA",
        "message": "✅ Railway conectado com sucesso!"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    print(f"🚀 Iniciando na porta {port}...")
    uvicorn.run("main:app", host="0.0.0.0", port=port)
