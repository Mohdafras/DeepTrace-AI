"""API tests use isolated SQLite storage and the real model where indicated.

Synthetic images verify mechanics only, never accuracy or known Real/Fake labels.
Deterministic stub outputs appear only in decision-boundary/error unit tests.
"""
import base64
from io import BytesIO
import json
import sqlite3

import numpy as np
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from main import app
from app.config import settings
from app.database import initialize_database
from app.services import prediction_service
from app.services.model_loader import ModelStore, model_store
from app.services.preprocessing import preprocess_image
from app.utils import image_utils


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "history.db"))
    with TestClient(app) as value:
        yield value


def image_bytes(fmt="PNG", color=(128, 128, 128), mode="RGB"):
    output = BytesIO()
    Image.new(mode, (224, 224), color).save(output, format=fmt)
    return output.getvalue()


def upload(client, data=None, name="synthetic.png", mime="image/png"):
    return client.post("/api/v1/predict", files={"file": (
        name, image_bytes() if data is None else data, mime)})


def assert_prediction_consistent(result):
    for field in ("real_probability", "fake_probability", "confidence_score", "threshold"):
        assert np.isfinite(result[field])
        assert 0 <= result[field] <= 1
    assert result["threshold"] == model_store.threshold
    assert result["real_probability"] + result["fake_probability"] == pytest.approx(1)
    expected = "REAL" if result["real_probability"] >= result["threshold"] else "FAKE"
    assert result["predicted_class"] == expected
    assert result["confidence_score"] == result[f"{expected.lower()}_probability"]


def test_health_loads_actual_model(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    value = response.json()
    assert value["model_loaded"] is True, model_store.error
    assert value["status"] == "ok"
    with settings.resolve(settings.threshold_path).open(encoding="utf-8") as handle:
        configured_threshold = json.load(handle)["threshold"]
    assert type(configured_threshold) in (int, float)
    assert 0 <= configured_threshold <= 1
    assert value["threshold"] == model_store.threshold == configured_threshold
    assert model_store.model.input_shape == (None, 224, 224, 3)
    assert model_store.model.output_shape == (None, 1)
    assert model_store.model.layers[-1].activation.__name__ == "sigmoid"


def test_actual_prediction_gradcam_and_history_crud(client):
    response = upload(client)
    assert response.status_code == 200, response.text
    result = response.json()
    assert_prediction_consistent(result)
    assert result["processing_time_ms"] > 0
    assert result["gradcam_overlay"] == result["gradcam_image"]
    # Synthetic pixels need not produce positive attention for every valid model.
    if result["gradcam_error"] is None:
        for field in ("gradcam_heatmap", "gradcam_overlay"):
            with Image.open(BytesIO(base64.b64decode(result[field], validate=True))) as img:
                assert img.format == "PNG"
                assert img.size == (224, 224)
    else:
        assert isinstance(result["gradcam_error"], str) and result["gradcam_error"]
        assert result["gradcam_heatmap"] is None
        assert result["gradcam_overlay"] is None
    listing = client.get("/api/v1/history").json()
    assert listing["total"] == 1
    detail = client.get(f"/api/v1/history/{result['record_id']}").json()
    for field in ("threshold", "predicted_class", "real_probability", "fake_probability", "confidence_score"):
        assert detail[field] == result[field]
    assert detail["original_filename"] == "synthetic.png"
    assert detail["created_at"].endswith("Z")
    assert not any(key.startswith("gradcam") or key == "image" for key in detail)
    assert client.delete(f"/api/v1/history/{result['record_id']}").status_code == 204
    assert client.get(f"/api/v1/history/{result['record_id']}").status_code == 404
    assert client.delete(f"/api/v1/history/{result['record_id']}").status_code == 404
    assert client.get("/api/v1/history").json() == {"items": [], "total": 0}


@pytest.mark.parametrize("fmt,extension", [("JPEG", "jpg"), ("JPEG", "jpeg"), ("PNG", "png"), ("WEBP", "webp")])
def test_supported_codecs(fmt, extension):
    with image_utils.decode_image(image_bytes(fmt), f"sample.{extension}") as image:
        batch = preprocess_image(image)
        assert batch.shape == (1, 224, 224, 3)
        assert batch.dtype == np.float32
        assert batch.min() > 100  # no accidental extra division by 255


def test_preprocessing_matches_original_tensorflow_resize():
    import tensorflow as tf
    values = np.arange(15 * 17 * 3, dtype=np.uint8).reshape(15, 17, 3)
    image = Image.fromarray(values)
    expected = tf.image.resize(values.astype(np.float32), (224, 224)).numpy()[None]
    np.testing.assert_array_equal(preprocess_image(image), expected)
    assert preprocess_image(image.convert("L")).shape == (1, 224, 224, 3)


@pytest.mark.parametrize("data,name", [(b"not an image", "broken.png"), (b"GIF89a", "file.gif"),
    (image_bytes("GIF"), "disguised.png"), (image_bytes("BMP"), "disguised.jpg")],
    ids=["corrupt-png", "gif-extension", "disguised-gif", "disguised-bmp"])
def test_invalid_uploads(client, data, name):
    assert upload(client, data, name).status_code == 415
    assert client.get("/api/v1/history").json()["total"] == 0


def test_empty_and_missing_upload(client):
    assert upload(client, b"").status_code == 400
    assert client.post("/api/v1/predict").status_code == 422


def test_oversized_upload(client):
    assert upload(client, b"x" * (10 * 1024 * 1024 + 1)).status_code == 413


def test_decoded_pixel_limit(client, monkeypatch):
    monkeypatch.setattr(image_utils, "MAX_IMAGE_PIXELS", 100)
    response = upload(client)
    assert response.status_code == 415
    assert "megapixel" in response.json()["detail"]


def test_sanitized_filename():
    assert image_utils.safe_filename("C:\\private\\photo.png") == "photo.png"
    assert image_utils.safe_filename("../private/photo.png") == "photo.png"
    assert image_utils.safe_filename("bad\nname.png") == "badname.png"


class StubSigmoid:
    """Unit-test output fixture, never used by the running application."""
    name = "test-only-sigmoid"
    def __init__(self, probability):
        self.probability = probability
    def __call__(self, batch, training=False):
        return np.array([[self.probability]], dtype=np.float64)


@pytest.mark.parametrize("probability,label", [(0.0834, "FAKE"), (0.4199, "FAKE"), (0.42, "REAL"), (0.45, "REAL"), (1, "REAL"), (0, "FAKE")])
def test_threshold_boundary_uses_real_score(client, monkeypatch, probability, label):
    monkeypatch.setattr(model_store, "model", StubSigmoid(probability))
    monkeypatch.setattr(model_store, "threshold", 0.42)
    monkeypatch.setattr(prediction_service, "generate_gradcam_images", lambda *args: {"heatmap": "", "overlay": ""})
    response = upload(client)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["predicted_class"] == label
    assert result["confidence_score"] == pytest.approx(probability if label == "REAL" else 1 - probability)
    assert result["threshold"] == 0.42
    assert client.delete("/api/v1/history").status_code == 204
    assert client.get("/api/v1/history").json()["total"] == 0


def test_gradcam_failure_keeps_real_prediction_and_logs(client, monkeypatch, caplog):
    def fail(*args):
        raise RuntimeError("test diagnostic: disconnected graph")
    monkeypatch.setattr(prediction_service, "generate_gradcam_images", fail)
    response = upload(client)
    assert response.status_code == 200
    assert_prediction_consistent(response.json())
    assert response.json()["gradcam_error"]
    assert response.json()["gradcam_overlay"] is None
    assert "disconnected graph" in caplog.text
    assert client.get("/api/v1/history").json()["total"] == 1


def test_unavailable_model(client, monkeypatch):
    monkeypatch.setattr(model_store, "model", None)
    assert client.get("/api/v1/health").json()["status"] == "degraded"
    assert upload(client).status_code == 503
    assert client.get("/api/v1/history").json()["total"] == 0


@pytest.mark.parametrize("probability", [float("nan"), float("inf"), -0.1, 1.1])
def test_invalid_model_output_is_reported(client, monkeypatch, probability):
    monkeypatch.setattr(model_store, "model", StubSigmoid(probability))
    assert upload(client).status_code == 500
    assert client.get("/api/v1/history").json()["total"] == 0


def test_cors_frontend_origins(client):
    for origin in ("http://localhost:5173", "http://127.0.0.1:5173"):
        response = client.options("/api/v1/predict", headers={"Origin": origin,
            "Access-Control-Request-Method": "POST"})
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin


def test_model_load_failure_logs(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(settings, "model_path", str(tmp_path / "missing.keras"))
    store = ModelStore()
    store.load()
    assert not store.loaded
    assert store.error
    assert "Model startup failed" in caplog.text


def test_boolean_threshold_rejected(tmp_path, monkeypatch):
    path = tmp_path / "threshold.json"
    path.write_text(json.dumps({"threshold": True}))
    monkeypatch.setattr(settings, "threshold_path", str(path))
    store = ModelStore()
    store.load()
    assert not store.loaded
    assert "numeric" in store.error


def test_actual_dark_image_inference(client):
    # An artificial black image has NO authenticity ground truth. This exercises
    # another actual model score, not a claim of real/fake detection accuracy.
    response = upload(client, image_bytes(color=(0, 0, 0)), "synthetic-dark.png")
    assert response.status_code == 200
    result = response.json()
    assert_prediction_consistent(result)
    assert client.get("/api/v1/history").json()["total"] == 1


def test_database_error_is_not_silently_ignored(client, monkeypatch, caplog):
    def fail(**kwargs):
        raise sqlite3.OperationalError("test database unavailable")
    monkeypatch.setattr(prediction_service, "create_record", fail)
    response = upload(client)
    assert response.status_code == 500
    assert "database unavailable" in caplog.text
    assert client.get("/api/v1/history").json()["total"] == 0


def test_attention_output_size_and_separate_images(monkeypatch):
    from app.services import gradcam_service
    monkeypatch.setattr(gradcam_service, "_attention_map", lambda *args: np.linspace(0, 1, 49, dtype=np.float32).reshape(7, 7))
    maps = gradcam_service.generate_gradcam_images(None, None, Image.new("RGB", (1600, 800), "white"), True)
    assert maps["heatmap"] != maps["overlay"]
    for encoded in maps.values():
        with Image.open(BytesIO(base64.b64decode(encoded))) as image:
            assert image.size == (1024, 512)


def test_legacy_history_migration_preserves_unknown_threshold(tmp_path, monkeypatch):
    path = tmp_path / "old.db"
    monkeypatch.setattr(settings, "database_path", str(path))
    with sqlite3.connect(path) as connection:
        connection.execute("""CREATE TABLE detections (id INTEGER PRIMARY KEY, original_filename TEXT,
            predicted_class TEXT, real_probability REAL, fake_probability REAL, confidence_score REAL,
            processing_time_ms REAL, created_at TEXT)""")
        connection.execute("INSERT INTO detections VALUES (1,'old.png','FAKE',0.1,0.9,0.9,10,'2026-01-01 00:00:00')")
    initialize_database()
    initialize_database()
    with TestClient(app) as client:
        record = client.get("/api/v1/history/1").json()
        assert record["threshold"] is None
        assert record["created_at"] == "2026-01-01T00:00:00Z"
