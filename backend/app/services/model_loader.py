"""Single-instance loading of the trained Keras model and threshold."""
import json
import logging

logger = logging.getLogger(__name__)
from pathlib import Path
from typing import Any

import tensorflow as tf
from app.config import settings


class ModelStore:
    def __init__(self) -> None:
        self.model: Any | None = None
        self.threshold: float | None = None
        self.error: str | None = None

    @property
    def loaded(self) -> bool:
        return self.model is not None and self.threshold is not None

    def load(self) -> None:
        """Load artifacts once; retain a safe diagnostic rather than crashing startup."""
        if self.loaded:
            return
        model_path = settings.resolve(settings.model_path)
        threshold_path = settings.resolve(settings.threshold_path)
        try:
            self._require_file(model_path, "Trained model")
            self._require_file(threshold_path, "Threshold configuration")
            with threshold_path.open(encoding="utf-8") as handle:
                payload = json.load(handle)
            value = payload.get("threshold")
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError("threshold.json must contain a numeric 'threshold' from 0 to 1.")
            model = tf.keras.models.load_model(model_path, compile=False)
            if model.input_shape != (None, 224, 224, 3) or model.output_shape != (None, 1):
                raise ValueError("Expected model input (None,224,224,3) and output (None,1).")
            activation = getattr(model.layers[-1], "activation", None)
            if activation is not tf.keras.activations.sigmoid:
                raise ValueError("Expected a single sigmoid classification output.")
            self.model = model
            self.threshold = float(value)
            self.error = None
            logger.info("Loaded %s: input=%s output=%s threshold=%.4f", model.name,
                        model.input_shape, model.output_shape, self.threshold)
        except Exception as exc:
            self.model = None
            self.threshold = None
            self.error = str(exc)
            logger.exception("Model startup failed; prediction endpoint will return 503.")

    @staticmethod
    def _require_file(path: Path, artifact: str) -> None:
        if not path.is_file():
            raise FileNotFoundError(f"{artifact} is missing. Place it in the configured model directory.")


model_store = ModelStore()
