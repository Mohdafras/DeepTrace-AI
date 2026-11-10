# DeepTrace AI

**Correction-work outcome — 2026-11-10:** See the [final completion report](completion-final/FINAL_COMPLETION_REPORT.md). The [audit](completion-final/TRAINING_AUDIT.md) found no demonstrated label/preprocessing or missing training-control defect to correct. The existing candidate's 39,044-image validation control reproduced exactly, but WSL stopped during the first alternative; the comparison is **incomplete**, with no new fitting, checkpoint-selection decision or new candidate export. All 106 protected/inspected source hashes were reverified unchanged. The original production backend was restored at threshold 0.42 and its endpoints checked. No independently qualified evaluation/demo image pack was obtained; [source research and plan](completion-final/INDEPENDENT_EVALUATION_PLAN.md), [historical curves](completion-final/historical-training-curves.html), [validation report](completion-final/VALIDATION_REPORT.md), and [launch commands](completion-final/LAUNCH_COMMANDS.md) document the evidence and limits. The old frozen test must not be replayed. No independently validated improvement or promotion is claimed.

**Final verification — 2026-11-10:** See [the completion report](completion-20261110/FINAL_REPORT.md) for current frozen-test results, all seven gates, application test evidence, and exact Windows/WSL startup commands. The production model remains unchanged at threshold 0.42; the candidate is **not eligible for promotion** because test REAL recall is below 80%. The dated records in `AUDIT.md` remain historical evidence.

A locally runnable academic deep-learning mini-project for **deepfake image classification**, using the existing trained EfficientNetB0 model, FastAPI and the original React interface. Results are automated model predictions—not proof of authenticity or a guaranteed forensic determination.

## Features

- Dashboard derived from SQLite-backed detection history, not sample detections.
- Drag/drop or browse JPEG/JPG, PNG and WEBP; preview, replace and remove before analysis.
- Actual multipart inference; REAL/FAKE label, both probabilities, selected-class score, threshold and processing time.
- Separate class-specific Grad-CAM heatmap and overlay, with an honest unavailable state.
- History list/detail, refresh, individual deletion and confirmed clearing.
- Responsive navigation, model information and backend connection status.
- Local-only inference; no external generative-AI API or API key is required.

## Architecture and layout

```text
Browser (React + TypeScript + Vite + Tailwind)
  -> POST /api/v1/predict, multipart field: file
FastAPI -> Pillow validation -> RGB float32 TensorFlow resize
  -> original EfficientNetB0 Keras model -> threshold decision
  -> Grad-CAM -> SQLite metadata -> JSON response -> browser
```

```text
backend/
  app/                 configuration, routes, validation, inference, Grad-CAM, history
  model/               original deepfake_model.keras and threshold.json
  data/                local SQLite metadata (ignored by Git)
  tests/               isolated API/model tests and evaluation-tool tests
  tools/evaluate.py    reproducible, non-training evaluation CLI
  main.py
  requirements.txt
deeptrace-ai---deepfake-image-detection-&-forensics/
  src/                 existing frontend architecture and visual design
  package.json
Start-DeepTrace.ps1
AUDIT.md               issues, implementation phases and verification record
```

The frontend directory name is retained intentionally. There is no duplicate backend or replacement frontend.

## Model contract verified from the saved artifact

- TensorFlow/Keras **EfficientNetB0**, frozen backbone in this export.
- Input **(None, 224, 224, 3)**, RGB float32 **0–255**.
- Horizontal flip / rotation augmentation and dropout are inactive during inference.
- Global-average pooling, dropout 0.3, Dense(1, sigmoid).
- **4,050,852 parameters; 1,281 trainable** in the export. This does not prove whether earlier training phases unfroze layers.
- EfficientNet's embedded rescaling/normalization is retained. **Do not divide input pixels by 255 externally.**
- Backend retains the previously effective TensorFlow bilinear resize with `antialias=False`. No new crop, EXIF rotation or external normalization was added.
- User-supplied label contract: **Fake=0, Real=1**. The model file alone does not encode the class-name mapping.
- `pReal = sigmoid output`, `pFake = 1 - pReal`.
- **REAL iff pReal >= 0.42**, otherwise FAKE, using `backend/model/threshold.json`.
- The displayed confidence is the score of the selected class, not calibrated certainty. A REAL classification can have a score below 50% because its threshold is 42%.

The original model and threshold were not retrained, replaced or tuned. Model SHA-256:

```text
2c5908debc8a05369adeeeb2d094d595bd981ef84ddc29a42e8f88ae177d7f16
```

### Dataset and evaluation evidence

The labeled dataset and retraining records are now available. The completed independent run at `/home/mohdaafras/deeptrace-evaluations/run-20261106-v2-fixed-test-20261109-01/evaluations/frozen-test-001` was reverified on 2026-11-10, without replaying inference. It contains exactly **10,905 frozen test records: 5,492 Fake and 5,413 Real**, processed once per model in manifest order.

| Frozen-test metric | Production (threshold 0.42) | Candidate (threshold 0.30225202441215515) |
|---|---:|---:|
| Accuracy | 69.89% | 86.91% |
| Balanced accuracy | 69.78% | 86.85% |
| REAL recall | 55.66% | 78.72% |
| FAKE recall | 83.90% | 94.97% |
| ROC AUC (REAL positive) | 0.800883 | 0.958100 |

Confusion matrices, rows actual/columns predicted in **Fake, Real** order:

```text
Production: [[4608, 884], [2400, 3013]]
Candidate:  [[5216, 276], [1152, 4261]]
```

The candidate passes six promotion gates but fails the required **REAL recall >= 80%** gate. It was not promoted, and thresholds were not adjusted. See the completion report and linked machine-readable evidence for per-class metrics, exact-binomial comparison, timing, and original hashes. Prior supplied counts/matrices are superseded by this verified frozen-test evidence, not silently presented as new measurements.

Original training provenance and related-image identities remain limitations. The label mapping is the documented training/manifest convention, not something the model archive can prove. Application smoke tests are separate: the production model misclassified the selected validation REAL example; the UI correctly displayed that actual result. Integration correctness is not detector accuracy.

## Requirements and installation (Windows PowerShell)

Use **Python 3.11** and **Node.js 22.12+ or a compatible newer release**. This workspace was tested with Python 3.11.6, Node 24.11.1, TensorFlow 2.19.1 and Keras 3.15.1. The existing Python dependency ranges were retained; no unnecessary upgrades were made.

From the project root:

```powershell
# Only if backend/.venv does not already exist:
py -3.11 -m venv backend/.venv

.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt

# Keep your existing .env; copy only if missing:
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }

Set-Location '.\deeptrace-ai---deepfake-image-detection-&-forensics'
npm ci
Set-Location ..
```

The model files must remain at `backend/model/deepfake_model.keras` and `backend/model/threshold.json`. A missing/incompatible model produces degraded health and a 503 prediction response; startup logs contain the detailed cause. CPU inference works; a GPU is not required. First startup/inference can be slower.

### Start backend — terminal 1

From the project root:

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8002 --reload
```

### Start frontend — terminal 2

From the project root:

```powershell
Set-Location '.\deeptrace-ai---deepfake-image-detection-&-forensics'
npm run dev
```

- **Frontend:** http://127.0.0.1:5173
- **Backend:** http://127.0.0.1:8002
- **Swagger:** http://127.0.0.1:8002/docs

Vite uses a strict port so it cannot silently move to an origin missing from CORS. The npm scripts invoke tool JavaScript entrypoints directly: this avoids Windows command-wrapper failures caused by the `&` in the preserved frontend folder name. Existing applications on port 3000 are left alone. Stop each service with Ctrl+C in its own terminal. Do not kill unrelated processes to free a port.

Optional Windows launcher:

```powershell
.\Start-DeepTrace.ps1
# Only when you have already started this project's backend on 8002:
.\Start-DeepTrace.ps1 -ReuseBackend
```

If local script policy prevents the launcher, use the two terminal commands rather than changing machine-wide execution policy.

### Configuration

Backend `.env` supports `MODEL_PATH`, `THRESHOLD_PATH`, `DATABASE_PATH`, `MAX_UPLOAD_SIZE_BYTES` and comma-separated `CORS_ORIGINS`. Relative backend paths resolve against the backend directory, not the shell's working directory.

The default frontend API base is `http://127.0.0.1:8002`; configuration is centralized in the frontend API service. The frontend environment example documents the Vite override. Browser runtime endpoint configuration is local to that browser. Vite environment values are public build-time configuration: **never put secrets in VITE variables**.

CORS includes localhost and 127.0.0.1 on ports 5173 and 3000. Adding an origin requires a backend restart. Keep this unauthenticated mini-project bound to loopback; CORS is not authentication. Do not expose its history/deletion APIs to the public internet.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/health` | API/model availability and configured threshold |
| POST | `/api/v1/predict` | Multipart `file`, up to 10 MiB (10,485,760 bytes) |
| GET | `/api/v1/history` | `{items, total}` newest first |
| GET | `/api/v1/history/{record_id}` | One metadata record |
| DELETE | `/api/v1/history/{record_id}` | Delete record; success 204 |
| DELETE | `/api/v1/history` | Clear metadata; success 204 |

```powershell
curl.exe -X POST http://127.0.0.1:8002/api/v1/predict -F "file=@C:\path\to\image.jpg"
```

Prediction fields: `record_id`, `filename`, `predicted_class`, `real_probability`, `fake_probability`, `confidence_score`, `threshold`, `processing_time_ms`, nullable `gradcam_heatmap`, nullable `gradcam_overlay`, legacy `gradcam_image` (overlay alias), and nullable `gradcam_error`. PNG fields are raw base64; display using `data:image/png;base64,`.

Processing time includes preprocessing, inference, Grad-CAM and local inference-queue wait, but not database insert, JSON serialization or network transfer. Historical pre-update times excluded Grad-CAM. Old rows preserve an unknown/null threshold instead of inventing one. SQLite timestamps are exposed explicitly as UTC.

## Privacy, validation and Grad-CAM

- SQLite retains original basename, class, scores, threshold, time and timestamp—not image bytes or Grad-CAM.
- Image previews are held in the browser; historical images cannot be restored after leaving/reloading. The UI explains this.
- FastAPI's upload parser may use a transient OS temporary file for multipart spooling; it is closed after the request. There is no permanent upload/image archive.
- File extension and decoded JPEG/PNG/WEBP content are both checked; corrupt, animated, oversized and >20-megapixel images are rejected. EXIF/metadata is not stored in SQLite.
- Grad-CAM targets the predicted class and final backbone convolution. Maps are capped at a 1024px longest edge, independently of the 224px model input.
- Pale-to-dark blue means lower-to-higher **relative model attention**, not a probability that a region is manipulated. Interpolation does not create pixel-level forensic localization.
- Missing gradients, zero positive activation, or graph errors leave the prediction intact, return an unavailable message and log the diagnostic. No fake heatmap is substituted.

## Tests

From the project root:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend/tests -q
```

Backend tests enter FastAPI lifespan, load the actual artifact and use temporary SQLite databases. They exercise inference and real Grad-CAM on synthetic images, validation failures, boundary decisions, CORS, history CRUD/migration and error diagnostics. Fixed probabilities in unit tests are explicitly test-only decision fixtures; runtime predictions always come from the Keras model.

Frontend commands, from its directory:

```powershell
npm test
npm run build
```

See the frontend README for browser automation commands. For browser tests that create/clear history, use this **separate disposable-history server**, not the real demo database:

```powershell
.\backend\.venv\Scripts\python.exe backend/tests/serve_isolated.py
# http://127.0.0.1:8003 — same real model, temporary SQLite history
```

Verified locally on 2026-11-05: **67 backend/evaluation tests passed, 26 frontend unit tests passed, 4 Edge browser scenarios passed, and the production build passed**. The browser scenarios exercised the actual saved model on synthetic inputs, not labeled accuracy evaluation.

The detailed verification record, changed-file inventory and untested items are in `AUDIT.md`. Non-fatal warnings remain for Starlette/httpx TestClient deprecation and Vite's >500 kB JavaScript chunk; dependency upgrades were not performed just to silence them.

## Reproducible evaluation tooling (other datasets only)

**Do not use the generic commands below to rerun or replace the completed approved frozen-test run.** That run has a separate one-shot safety framework and verified completion evidence. These legacy CLI examples apply only to separately authorized datasets; they deduplicate/validate data differently from the approved frozen-membership evaluation.

Use the original immutable layout, e.g. `D:\datasets\deepfake\Train\Fake`, `Train\Real`, `Validation\Fake`, `Validation\Real`, `Test\Fake`, `Test\Real`. Lowercase `train/valid/test` is also supported. No automatic splitting, training or relabeling occurs.

Create an output parent outside the dataset/model folders, then use a **new** report directory each time:

```powershell
$py = '.\backend\.venv\Scripts\python.exe'
$tool = '.\backend\tools\evaluate.py'
$data = 'D:\datasets\deepfake'

# Fixed saved threshold on untouched test data:
& $py -I -B $tool evaluate --dataset-root $data --split test --output-dir 'D:\evaluation-runs\test-001'

# Optional balanced smoke subset (not representative deployment precision):
& $py -I -B $tool evaluate --dataset-root $data --split test --balanced-per-class 100 --seed 42 --output-dir 'D:\evaluation-runs\test-small-001'

# Advisory validation-only comparisons; never edits threshold.json:
& $py -I -B $tool validation-thresholds --dataset-root $data --thresholds 0.35 0.42 0.50 --output-dir 'D:\evaluation-runs\validation-001'

# Preserve genuine operator-supplied labels in a small test collection:
& $py -I -B $tool collect-known --real 'D:\known\camera.jpg' --fake 'D:\known\generated.jpg' --label-source 'Verified source records' --output-manifest 'D:\evaluation-runs\known.json'
& $py -I -B $tool evaluate --known-manifest 'D:\evaluation-runs\known.json' --output-dir 'D:\evaluation-runs\known-001'
```

Reports include accuracy, per-class precision/recall/F1, confusion matrix, explicit real-as-fake and fake-as-real errors, ROC-AUC, Brier score, intervals, per-image CSV and reproducibility manifests. Every image across all splits is hashed before selection; this costs O(total dataset bytes). Exact duplicates/cross-split overlap/conflicting labels are refused. Hashes do not detect shared identities or perceptual duplicates. Inspect those manually using dataset provenance. Ground-truth labels in class folders or known-image manifests remain the operator's responsibility.

The CLI never selects a threshold using test performance, changes the active model/threshold, or treats model output as ground truth. Recover the Colab notebook before claiming exact reproduction of its training process. Retraining requires a separate deliberate decision, a model backup and an untouched-test comparison—not automatic action by this project.

## Known limitations

- Original training/notebook provenance has not been fully recovered; the current frozen test and retraining records do not independently prove all original training choices.
- The verified production test matrix indicates substantial real-image false alarms. This application integration does not improve the trained classifier's generalization.
- Domain shift, resizing, compression and dataset shortcuts can cause confident errors. No face detector, forensic certification or calibrated uncertainty is claimed.
- CPU inference/Grad-CAM is serialized for this local demonstration; this is not a high-throughput production service.
- History is currently returned as a whole and paginated in the frontend; very large histories need server-side pagination.
- No authentication, multi-user isolation or production deployment hardening. Keep local.
