import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import alertas, clusters, detalhe, fatores, kpi, painel

load_dotenv()

app = FastAPI(title="MVP Locaweb — AIOps Incidentes API")

origins = os.getenv("API_CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(painel.router)
app.include_router(detalhe.router)
app.include_router(kpi.router)
app.include_router(fatores.router)
app.include_router(clusters.router)
app.include_router(alertas.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
