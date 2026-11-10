# DeepTrace retraining runbook

Readable aggregate report: `backend/dataset-inspection-report.html`. Shareable Artifact publication was attempted but unavailable under this session's token-based authentication; the report remains local. No dataset images or manifests were published.

## Resumed audit — 2026-11-06

- The first continuation retry stopped before TensorFlow loading at 1.99 GiB free RAM; no model predictions or training occurred during that retry.
- After the user freed memory and confirmed continuation, preflight measured 3.533 GiB free RAM and 174.47 GiB free disk. The same prepared run's audit is now running; this is not a completed validation evaluation yet. Log: `model/candidates/run-20261106-v2/audit-20261106-1035.log`.
- Model loading succeeded: 4,050,852 total parameters / 1,281 trainable, internal preprocessing verified by inspection, and TensorFlow GPU list empty. The saved 32-image benchmark measured 13.65 images/s including warm-up; this is not training throughput.
- Training-only safeguards were corrected: configured memory minimum during training/validation and retained per-epoch, per-attempt full-model archives. Regression tests for these changes are pending; a concurrent test launch was declined at 2.251 GiB free RAM to avoid competing with the audit.
- Original source/test/runbook copies were preserved in the run's `source-before-training-fixes-20261106/`. Prepared configuration, manifests, production artifacts and original backups are unchanged. Training has not started.
- The user explicitly approved downloading official ImageNet EfficientNetB0 no-top weights. The 16,705,208-byte file is cached inside the run; Keras MD5 and SHA-256 are recorded in `imagenet_weights_provenance.json`. No dataset or training outputs were uploaded.

## Earlier execution status — 2026-11-06 (before resumed audit)

- Dataset located at the exact supplied path below; original files are read-only inputs.
- Exhaustive inspection completed: 190,335 readable JPEG images, all 256×256; 1,802,944,866 bytes (1.80 GB / 1.68 GiB); zero corrupt files or unknown/conflicting duplicate labels. Integrity-qualified original counts:

| Split | Fake | Real | Total |
|---|---:|---:|---:|
| Train | 70,001 | 70,001 | 140,002 |
| Validation | 19,641 | 19,787 | 39,428 |
| Test | 5,492 | 5,413 | 10,905 |
| Total | 95,134 | 95,201 | 190,335 |

- Corrected full inspection completed in 2,421.39 seconds (40.36 minutes): `backend/dataset-inspection-20261106-verified/inspection.json`.
- Exact-byte and decoded-pixel hashes agree: 17,135 duplicate pairs, comprising 11,417 Train–Train, 5,334 Train–Validation, and 384 Validation–Validation pairs. No duplicates involve Test. Of the pairs, 17,130 are Real and 5 Fake.
- Prepared run: `backend/model/candidates/run-20261106-v2/`. Manifest-only exclusions leave Train Fake=69,996 / Real=53,255 and Validation Fake=19,641 / Real=19,403. Test Fake=5,492 / Real=5,413 remains unchanged. Every excluded reference is recorded; no originals were deleted.
- Execution of `audit -> train -> finalize` was attempted. The audit stopped before TensorFlow loading because only 1.50 GiB physical RAM remained after manifest loading, below the configured 2.00 GiB guard. No training, full validation scoring or final test inference occurred. The user chose to free RAM; wait for sufficient resources before retrying.
- `backend/dataset-inspection-20261106/` is an **aborted preliminary scan**, not a completed integrity report. A PNG verification-order defect was detected by regression tests, corrected, and the scan restarted. Do not use the preliminary inventory.
- No candidate has been trained or promoted. No validation/test accuracy is claimed.
- The test split has been accessed only for directory enumeration and integrity hashing/decoding, not model inference or model/threshold selection.

## Preserved artifacts and model audit

Verified backup: `backend/model/backups/original-20261106/` contains the original model, threshold, and hash manifest.

| File | SHA-256 |
|---|---|
| deepfake_model.keras | `2c5908debc8a05369adeeeb2d094d595bd981ef84ddc29a42e8f88ae177d7f16` |
| threshold.json | `c14467d81bc0323b9464c7418586211248858260bd3a77625b04339d87ca88dd` |

The active artifacts remain unchanged. Actual loading established:

- EfficientNetB0, float32 `(None,224,224,3)` input and one sigmoid output.
- 4,050,852 total parameters; the saved state has a frozen backbone and 1,281 trainable classification-head parameters.
- Internal `/255`, ImageNet normalization, and EfficientNet rescaling are present. Backend RGB 0–255 / TensorFlow bilinear resize is consistent with this model input contract.
- All saved weights are finite. The configured real-score threshold is 0.42.
- The backend interprets output as pReal and classifies REAL when `pReal >= threshold`; the frontend preserves that decision. Original training `class_indices` and history are unavailable, so training-label provenance and overfitting are not established.
- The saved state alone is not enough to identify the cause of false-FAKE predictions. Validation score distributions and class-specific errors are required.

## Hardware constraints

This Windows host has approximately 16 GB RAM and an NVIDIA RTX 3050 with 6 GB VRAM. Installed TensorFlow 2.19.1 is **not a CUDA build**, reports no GPUs, and WSL is not installed. No dependencies or drivers were upgraded.

Observed free RAM during inspection fluctuated around 0.7–1.1 GiB. Training/audit commands require 2 GiB free physical RAM by default and refuse to start below that limit. Close unused applications yourself or use a compatible GPU training environment; the tooling never stops other processes. CPU training on 140,002 images can take many hours. The audit saves a measured small forward-pass benchmark before full validation. That benchmark is not training throughput or an accuracy estimate.

## Commands from the project root (PowerShell)

Use the project Python, not the Windows Store `python` alias. `-I` prevents dataset-adjacent modules from hijacking imports.

```powershell
$python = '.\backend\.venv\Scripts\python.exe'
$dataset = 'C:\Users\mohda\OneDrive\Desktop\Deepfake-Image-Detection\deeptrace-ai---deepfake-image-detection-&-forensics\dataset'
```

### 1. Inspect once into a new output directory

The verified scan is complete. The command below records how it was run; use a different new output directory if a fresh inspection is needed.

```powershell
& $python -I -B backend/tools/inspect_dataset.py `
  --dataset-root $dataset `
  --output-dir backend/dataset-inspection-20261106-verified `
  --workers 4
```

An existing output directory is never overwritten. If interrupted, retain it as partial evidence and rerun to a **different** output directory. The scan emits:

- `inspection_started.json`: source, discovered file count, start time.
- `inventory.jsonl`: per-file SHA-256, decoded-RGB SHA-256, format, dimensions, split/label, readability and errors. Partial lines are not a completed manifest.
- `inspection.json`: completed aggregate report with counts, size, class ratios, integrity issues and duplicate totals.
- `invalid_files.json`: all invalid/unreadable file records, not silently ignored.
- `duplicates.json`: exact-byte and exact-decoded-pixel duplicate groups, including cross-split and conflicting-label flags.
- `directories.json`: discovered directory structure.

Hashing does **not** establish identity/source-video separation or detect all near-duplicates. Directory labels are supplied ground truth, not independently authenticated images.

### 2. Freeze the data plan and back up originals

This step has already completed for `run-20261106-v2`; do not repeat preparation into that existing directory. The command below records its configuration.

```powershell
$run = 'backend/model/candidates/run-20261106-v2'
& $python -I -B backend/tools/retrain.py prepare `
  --inspection backend/dataset-inspection-20261106-verified `
  --run-dir $run --batch-size 4 --threads 4 `
  --head-epochs 5 --fine-epochs 8 --seed 42
```

The preparation command refuses corrupt files, unknown labels, or contradictory labels on identical decoded pixels. It never guesses a class or relabels an image.

Duplicate exclusion is a **manifest-only** operation: test membership is unchanged; identical-pixel copies are excluded from training before validation/test, and from validation before test. First path is retained within training/validation. Every excluded reference is recorded. This uses all remaining unique, reliably labeled training examples, without deleting originals. Repeated test pixels prevent promotion because a nominal image-wise significance test would not be reliable.

### 3. Audit and benchmark the existing model on validation only

```powershell
& $python -I -B backend/tools/retrain.py audit --run-dir $run
```

The fixed existing threshold remains 0.42. Reports include class-specific score quantiles, accuracy, Fake-positive precision/recall/F1, specificity (=Real recall), balanced accuracy, false-positive/negative rates, confusion matrix, per-image errors, ROC and precision–recall coordinates/plots. No test predictions occur here.

### 4. Train and select on validation

```powershell
# Official weights were downloaded with explicit user approval and verified.
# Keep Keras configuration/cache inside the project (no dataset uploads).
$env:KERAS_HOME = Join-Path (Resolve-Path $run).Path 'keras-cache'
& $python -I -B backend/tools/retrain.py train --run-dir $run
```

- Fresh ImageNet EfficientNetB0 weights, not a warm-start from the existing head. The approved official download is cached at `$run/keras-cache/models/efficientnetb0_notop.h5`; installed Keras MD5 and an independently recorded SHA-256 were verified. See `$run/imagenet_weights_provenance.json`. Use the project-local `KERAS_HOME` above; do not download alternate weights silently.
- Explicit Fake=0, Real=1; same RGB resize/pixel contract as serving.
- Seeded horizontal flips and small rotations, no destructive crops or aggressive color transforms.
- Stage 1: frozen backbone, Adam 1e-3, up to 5 epochs.
- Stage 2: only block6/block7/top-convolution layers trainable, Adam 1e-5, up to 8 epochs; all BatchNormalization stays frozen and backbone executes with `training=False`.
- Balanced class weights derived from the final training manifest.
- Path shuffling, one decoder worker, batch 4, one-batch prefetch, no full-image RAM cache.
- Validation-loss checkpoint selection across both stages, early stopping and learning-rate reduction.
- Checkpoints every 500 batches, retaining current/previous recovery states, plus best `.keras` checkpoints and CSV training histories.
- A separate full-model `.keras` archive is saved after every completed epoch under `epoch_checkpoints/<stage>/attempt-NNN/`. Each resumed stage gets a new attempt directory, preserving earlier copies of repeated epochs. These archives do not change validation-loss model selection; rolling backups remain the automatic recovery mechanism.
- The configured 2 GiB free-physical-RAM minimum is enforced at each training epoch start and before each training/validation batch. The former 0.25 GiB epoch guard was corrected before candidate training. A low-memory stop does not terminate unrelated processes and may require replaying batches since the last recovery checkpoint.

Resume after interruption by running the same `train` command with the same project-local `KERAS_HOME`. Model/optimizer checkpoint recovery is provided, but an interrupted epoch can repeat batches; augmentation/shuffle/callback state is not guaranteed bitwise identical. Preserve all checkpoint and history files. `last_error.json` records why execution stopped.

Threshold selection uses **validation only**: maximize balanced accuracy subject to both class recalls >=0.80; ties favor higher Real recall and then proximity to 0.5. If no threshold meets both recall constraints, record the unconstrained optimum but mark it ineligible for promotion. The complete threshold sweep is retained.

The candidate, threshold, and selection/config hashes are frozen before test access. Candidate file: `$run/deepfake_model_v2.keras`; threshold: `$run/threshold.json`.

### 5. Final test, once for fixed artifacts

```powershell
& $python -I -B backend/tools/retrain.py finalize --run-dir $run
```

This creates a test lock before any predictions. Both fixed models are scored on the same complete original test split. Thresholds are not tuned. The comparison requires strictly improved accuracy and balanced accuracy, neither class recall worse than the existing model, >=0.80 recall for each class, the validation recall constraint, and an exploratory paired one-sided exact test p<0.05. Dependence among related images can invalidate that test; original-model test exposure is unknown.

A failed candidate is retained as evidence, not activated. The CLI does **not automatically promote any candidate**, even if the numeric gates pass. Inspect final results and actual-model Grad-CAM/API compatibility before activation. Keep the original recoverable.

If final evaluation is interrupted, repeat `finalize` only with the same locked artifacts. Completed score caches are reused; an interrupted unfinished model pass may be recomputed without any model/threshold change.

## Application integration and checks

Existing environment-backed `MODEL_PATH` / `THRESHOLD_PATH` settings already support a separate candidate directory. Health exposes loaded model name and threshold. No active path change has been made.

The frontend now excludes `dataset/` from Vite watching, development-server file access, and Tailwind source scanning. The current app design and API response shape are preserved. Dataset/report/checkpoint paths are Git-ignored.

Model-dependent tests no longer assume that a neutral image must receive a particular probability or classification from the old weights. Boundary tests explicitly set their own threshold fixture. These mechanics tests are **not accuracy measurements**.

Fresh checks completed in this continuation:

- Full backend suite: **86 passed** (one existing Starlette/httpx deprecation warning), including 19 new inspection/metrics/safety/recovery tests.
- The recovery tests cover rejected dataset output paths, directory traversal errors, failed JSON publication, interrupted report bundles, immutable evaluation inputs and idempotent candidate copies.
- Frontend unit tests: 26 passed.
- Frontend TypeScript/production build: passed; existing >500 kB bundle warning remains.
- Live backend health: loaded, threshold 0.42.
- Actual labeled API smoke: `Validation/Real/real_0.jpg` was predicted FAKE (pReal 0.3352174461), while `Validation/Fake/fake_0.jpg` was predicted FAKE (pReal 0.2784608305). Both produced valid PNG heatmaps/overlays and correct probability/threshold semantics. History roundtrips passed; only the two records created by this check were deleted. This reproduces one genuine-image error, not a generalization estimate. Evidence: `backend/labeled-api-smoke-20261106.json`.
- Fresh Vite instance: frontend HTTP 200, both tested dataset-image URLs HTTP 403. The previously stalled frontend on 5173 was restarted with explicit user approval; the temporary 5174 instance was stopped. Backends and other projects were not stopped.
- Actual labeled browser smoke: **2 scenarios passed**, desktop 1440×1000 with a Real validation image and mobile 390×844 with a Fake validation image. UI labels/probabilities/confidence/threshold matched real API responses; original/heatmap/overlay decoded; history detail worked; corrupt/unsupported selection errors were tested; no horizontal page overflow. Screenshots were visually inspected. Only the two records created by these scenarios were deleted. Evidence: `backend/browser-labeled-20261106/results.json` and local screenshots. The stored screenshots contain dataset faces and have not been published.
- The pre-existing four-scenario Playwright suite was collected/type-checked but not rerun; the new two-scenario labeled smoke is separate evidence.
- Full validation/test evaluation and retraining remain blocked by free RAM.

```powershell
& $python -B -m pytest backend/tests -q --tb=short
# Use node directly for --prefix paths containing &, avoiding npm.cmd argument parsing:
node 'C:/Program Files/nodejs/node_modules/npm/bin/npm-cli.js' `
  --prefix 'deeptrace-ai---deepfake-image-detection-&-forensics' test
node 'C:/Program Files/nodejs/node_modules/npm/bin/npm-cli.js' `
  --prefix 'deeptrace-ai---deepfake-image-detection-&-forensics' run build
```

## Start the existing application

Use separate terminals. Do not start duplicates if these ports are already occupied.

```powershell
# Terminal 1, project root:
.\backend\.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8002

# Terminal 2, project root:
node 'C:/Program Files/nodejs/node_modules/npm/bin/npm-cli.js' `
  --prefix 'deeptrace-ai---deepfake-image-detection-&-forensics' run dev
```

Frontend: http://127.0.0.1:5173 · API: http://127.0.0.1:8002 · Swagger: http://127.0.0.1:8002/docs

For browser tests, use `backend/tests/serve_isolated.py` on 8003, which uses the real model and disposable SQLite history. Never point history-clearing browser tests at the normal application database.
