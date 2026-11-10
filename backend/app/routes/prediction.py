"""Prediction endpoint with bounded uploads and off-loop CPU processing."""
import logging
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.schemas import PredictionResponse
from app.services.prediction_service import ModelUnavailableError, predict
from app.utils.image_utils import decode_image, safe_filename

logger = logging.getLogger(__name__)
router = APIRouter()


def _process(content: bytes, filename: str):
    try:
        image = decode_image(content, filename)
    except ValueError as exc:
        raise HTTPException(415, str(exc)) from exc
    try:
        return predict(image, filename)
    except ModelUnavailableError as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        logger.exception("Prediction or metadata persistence failed.")
        raise HTTPException(500, "Analysis failed. Check backend logs, then retry.") from exc
    finally:
        image.close()


@router.post("/predict", response_model=PredictionResponse, status_code=status.HTTP_200_OK)
async def predict_image(file: UploadFile = File(..., description="JPG, JPEG, PNG, or WEBP image up to 10 MB.")):
    """Classify an uploaded image; never intentionally retain its contents."""
    try:
        filename = safe_filename(file.filename or "")
        if not filename:
            raise HTTPException(400, "A filename is required.")
        content = await file.read(settings.max_upload_size_bytes + 1)
        if len(content) > settings.max_upload_size_bytes:
            raise HTTPException(413, "Image exceeds the 10 MB upload limit.")
        if not content:
            raise HTTPException(400, "The uploaded file is empty.")
        return await run_in_threadpool(_process, content, filename)
    finally:
        await file.close()
