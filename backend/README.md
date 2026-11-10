# Deepfake Image Detection Backend

FastAPI backend for a binary EfficientNetB0 image classifier. The model's sigmoid output is interpreted as the **REAL** probability; outputs below the configured threshold are classified as **FAKE**. Uploaded image contents are processed in memory and are not stored. SQLite retains detection metadata only.

## Architecture

`main.py` configures FastAPI, CORS, routes, and lifecycle startup. Startup creates SQLite storage and loads the Keras model once. Routes delegate validation, preprocessing, inference, Grad-CAM, and history operations to focused modules in `app/`.

## Layout

```
backend/
  app/                 # configuration, routes, services, utilities
  model/               # place private trained artifacts here
  uploads/             # reserved; images are not persisted by default
  tests/               # API contract tests
  main.py
```

## Required artifacts

Copy these files from Google Drive into `backend/model/` before starting:

```
backend/model/deepfake_model.keras
backend/model/threshold.json
```

`threshold.json` must contain, for example:

```json
{"threshold": 0.42}
```

## Setup and start

From `backend/`, create and activate a virtual environment, then install and start:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
uvicorn main:app --host 127.0.0.1 --port 8002 --reload
```

Open Swagger UI at `http://127.0.0.1:8002/docs`. Configure frontend origins in `.env` with `CORS_ORIGINS`; comma-separate multiple origins.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/v1/predict` | Upload JPG/JPEG/PNG/WEBP (max 10 MB) |
| GET | `/api/v1/history` | List detections |
| GET | `/api/v1/history/{record_id}` | Retrieve one detection |
| DELETE | `/api/v1/history/{record_id}` | Delete one detection |
| DELETE | `/api/v1/history` | Clear detection metadata |
| GET | `/api/v1/health` | Check API/model status |

Example request:

```powershell
curl.exe -X POST http://127.0.0.1:8002/api/v1/predict -F "file=@C:\path\to\image.jpg"
```

Example response (values shown are illustrative):

```json
{"record_id": 1, "filename": "image.jpg", "predicted_class": "REAL", "real_probability": 0.87, "fake_probability": 0.13, "confidence_score": 0.87, "threshold": 0.42, "processing_time_ms": 91.2, "gradcam_image": "...", "gradcam_error": null}
```

`confidence_score` is the model score for the selected class; it is not claimed to be a calibrated probability. A frontend can submit a multipart `file` field to `/api/v1/predict`, display response fields and decode `gradcam_image` with `data:image/png;base64,`.

## Verified model and attention contract

The saved model was loaded and inspected: `(None,224,224,3)` RGB float32 0–255 input, frozen EfficientNetB0, global-average pooling, dropout and one sigmoid output. Fake=0 / Real=1 is the supplied label contract. Preserve TensorFlow bilinear resizing and in-model normalization; do not add external `/255` scaling.

Grad-CAM reconnects the actual backbone's `top_conv` output and classification tail, with augmentation/dropout disabled. Predictions expose **separate** raw-base64 PNG fields `gradcam_heatmap` and `gradcam_overlay`; `gradcam_image` remains an overlay alias. Pale-to-dark blue is relative class attention, not evidence that an area was edited. Generated images have a maximum 1024px longest edge. A failure leaves the prediction intact, sets `gradcam_error`, and logs a traceback.

History retains metadata only. New rows retain their threshold; old rows have `threshold: null`. All API timestamps are explicit UTC. Prediction processing time now includes Grad-CAM (but not DB insertion, serialization or network time).

## Verification

From the project root, run `backend/.venv/Scripts/python.exe -m pytest backend/tests -q`. Tests isolate SQLite in temporary directories and enter application lifespan. Actual-model synthetic-image checks are functional smoke tests, not accuracy evaluation. For browser testing without deleting demonstration history, run `backend/.venv/Scripts/python.exe backend/tests/serve_isolated.py` on port 8003.

See the root [README](../README.md) and [audit record](../AUDIT.md) for complete startup instructions, frontend integration, actual test evidence, evaluation commands, missing dataset/training artifacts and limitations.
