from fastapi import APIRouter

router = APIRouter(prefix="/brokers", tags=["Corretoras"])

@router.get("/")
async def get_brokers():
    return {
        "brokers_disponiveis": [
            "Deriv",
            "Quotex",
            "IQ Option",
            "Binomo",
            "PocketOption",
            "OlympTrade",
        ],
        "status": "Ativo e pronto para conexão automática"
    }
