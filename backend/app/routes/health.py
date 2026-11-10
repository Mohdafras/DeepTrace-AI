"""Service health endpoint."""
import tensorflow as tf
from fastapi import APIRouter
from app.schemas import HealthResponse
from app.services.model_loader import model_store

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok" if model_store.loaded else "degraded",
        model_loaded=model_store.loaded,
        model_name=getattr(model_store.model, "name", None), tensorflow_version=tf.__version__,
        threshold=model_store.threshold,
        model_error=None if model_store.loaded else "Model unavailable; inspect backend startup logs.")
