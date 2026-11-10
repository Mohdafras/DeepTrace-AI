"""Application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import initialize_database
from app.routes import health, history, prediction
from app.services.model_loader import model_store


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialise persistent storage and load the configured model once."""
    initialize_database()
    model_store.load()
    yield


app = FastAPI(
    title="Deepfake Image Detection API",
    description="Classifies an uploaded image as REAL or FAKE using the configured EfficientNetB0 model.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)
app.include_router(prediction.router, prefix="/api/v1", tags=["Prediction"])
app.include_router(history.router, prefix="/api/v1", tags=["History"])
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
