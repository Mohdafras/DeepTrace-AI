"""Inference orchestration using the saved model's real output only."""
import logging
from threading import Lock
from time import perf_counter

import numpy as np
from PIL import Image

from app.services.gradcam_service import generate_gradcam_images
from app.services.history_service import create_record
from app.services.model_loader import model_store
from app.services.preprocessing import preprocess_image

logger = logging.getLogger(__name__)
_inference_lock = Lock()


class ModelUnavailableError(RuntimeError):
    pass


def predict(image: Image.Image, filename: str) -> dict[str, object]:
    """Serialize local CPU inference; persist metadata after attention processing."""
    if not model_store.loaded:
        raise ModelUnavailableError("Model is not loaded; inspect backend startup logs.")
    start = perf_counter()
    with _inference_lock:
        batch = preprocess_image(image)
        output = np.asarray(model_store.model(batch, training=False))
        if output.shape != (1, 1) or not np.isfinite(output).all():
            raise RuntimeError("Model must return one finite sigmoid probability per image.")
        real_probability = float(output[0, 0])
        if not 0 <= real_probability <= 1:
            raise RuntimeError("Model output is outside the expected 0–1 range.")
        fake_probability = 1.0 - real_probability
        predicted_real = real_probability >= model_store.threshold
        predicted_class = "REAL" if predicted_real else "FAKE"
        confidence = real_probability if predicted_real else fake_probability
        gradcam_heatmap, gradcam_overlay, gradcam_error = None, None, None
        try:
            maps = generate_gradcam_images(model_store.model, batch, image, predicted_real)
            gradcam_heatmap, gradcam_overlay = maps["heatmap"], maps["overlay"]
        except Exception:
            # No image bytes or original filenames in diagnostics.
            logger.exception("Grad-CAM failed for model %s; keeping prediction.", model_store.model.name)
            gradcam_error = "No usable Grad-CAM map was generated. Prediction is available; see backend logs for details."
    # Includes preprocessing, model inference, attention and any inference queue wait.
    # Excludes DB insert, response serialization and network transfer.
    processing_time_ms = round((perf_counter() - start) * 1000, 2)
    record_id = create_record(original_filename=filename, predicted_class=predicted_class,
        real_probability=real_probability, fake_probability=fake_probability,
        confidence_score=confidence, threshold=model_store.threshold,
        processing_time_ms=processing_time_ms)
    return {"record_id": record_id, "filename": filename, "predicted_class": predicted_class,
        "real_probability": real_probability, "fake_probability": fake_probability,
        "confidence_score": confidence, "threshold": model_store.threshold,
        "processing_time_ms": processing_time_ms, "gradcam_image": gradcam_overlay,
        "gradcam_heatmap": gradcam_heatmap, "gradcam_overlay": gradcam_overlay,
        "gradcam_error": gradcam_error}
