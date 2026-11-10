# DeepTrace AI — final correction-work report

**Date:** 2026-11-10
**Outcome:** Audit and control validation completed; checkpoint comparison interrupted; no new model approved.
**Promotion decision:** Keep the original production model. The requested independently validated improved model and independent 40-image demonstration pack were **not achieved**.

## Executive summary

The audit found no demonstrated label inversion, external-normalization error, missing class weighting, missing early stopping or unfrozen-BatchNormalization defect to correct. Additional fitting was therefore not started merely to produce a new model file. A locked validation-only comparison of existing fine-tuning checkpoints was attempted instead.

The actual candidate control completed all **39,044 validation records** and reproduced its saved confusion matrix and key metrics exactly. WSL later stopped during the first alternative, terminating both the experiment and the existing backend. The cause remains undetermined. Partial evidence was preserved; inference was not retried; no alternative was selected.

After WSL was reopened for inspection, **106 protected/inspected original file hashes and seven staged checkpoint hashes were verified unchanged**. The unchanged production backend was restored. At **07:00:26 UTC**, backend health, frontend document, Swagger and CORS checks all passed. This is point-in-time availability evidence, not a new browser prediction/Grad-CAM test or classification-accuracy claim.

Public-source research did not establish a genuinely independent, provenance-verified image pack. No substitute training/validation/old-test images were exported. No independent test results, demonstration filenames or demonstration predictions were fabricated.

## What was established

### Training/data audit

See [TRAINING_AUDIT.md](TRAINING_AUDIT.md) for counts, duplicate analysis, source citations, label/preprocessing contracts, weighting, augmentation, optimizer, stopping/checkpoint policies, recovery history, fitting trends and limitations.

- Effective training: 69,996 FAKE + 53,255 REAL = **123,251**.
- Effective validation: 19,641 FAKE + 19,403 REAL = **39,044**.
- Raw train/validation exact duplicates exist, but effective manifest exact encoded-/recorded-pixel-hash overlap is zero. Identity/source/near-duplicate leakage remains unresolved.
- Class weighting was already used. REAL-positive sigmoid convention and FAKE-positive reporting conventions are consistent.
- Some late fitting and repeated validation selection are documented. Their contribution to the independent-performance gap is not quantified, and no causal root cause is claimed.

### Completed control validation only

| Metric | Fresh control validation |
|---|---:|
| Accuracy | 96.7601% |
| Balanced accuracy | 96.7624% |
| REAL recall | 97.1396% |
| FAKE recall | 96.3851% |
| Macro F1 | 96.7601% |
| REAL-positive ROC AUC | 0.9954448744 |
| Brier score | 0.02623040588 |
| 10-bin validation ECE | 0.01499982960 |

Matrix, actual rows/predicted columns in **FAKE, REAL** order:

```text
[[18931, 710],
 [  555, 18848]]
```

These are **reused validation results for the existing candidate**, not independent test results, new-model improvement or calibrated certainty. The threshold remained **0.30225202441215515**. See [VALIDATION_REPORT.md](VALIDATION_REPORT.md) for both-class precision, error rates, calibration caveats, resource observations and the interruption record.

### Comparison interruption

- Control: completed and checked from its saved prediction CSV without rerunning inference.
- Fine epoch 1: partial CSV/logs only; no completion marker and no full-set metrics used.
- Fine epochs 2, 3, 5, 6, 7: never started.
- Meaningful-improvement rules: not relaxed, but a complete comparison was unavailable.
- Selection/export: **none**. The seven staged files are copies of prior checkpoints, not newly trained candidates.
- Resource safeguards: one worker at a time, 3,584 MiB TensorFlow GPU limit and RAM/GPU/RSS/timeout monitoring. Last retained samples were above the free-memory guards; those samples do not establish why WSL stopped or rule out an unobserved event.
- No automatic retry or crash-cause claim was made. The normal successful finalizer was not executed.

## Requested deliverable status

| # | Requested item | Delivered status |
|---|---|---|
| 1 | Training audit report | **Completed:** [TRAINING_AUDIT.md](TRAINING_AUDIT.md), detailed prior audit copies and new hash evidence in the experiment. |
| 2 | New training script/configuration | **No new fitting script/run:** no audit-supported fitting correction was established. New controlled validation [source snapshots](experiment-scripts/) and [locked configuration](experiment-config.json) are supplied; they are not labeled as retraining. |
| 3 | Training history and learning curves | **Historical only:** [interactive curves](historical-training-curves.html), [full-precision table](historical-training-table.csv), and copied head/fine histories. No new training history exists. |
| 4 | Best new candidate in separate directory | **Not produced:** comparison incomplete. Existing checkpoints were staged separately; production and the old candidate are unchanged. |
| 5 | Validation metrics/confusion matrix | **Control completed:** [validation report](VALIDATION_REPORT.md), [metrics JSON](control-validation-metrics.json), [calibration JSON](control-validation-calibration.json). Alternative comparison incomplete. |
| 6 | New independent evaluation report | **Not executed:** [source research and acquisition/evaluation plan](INDEPENDENT_EVALUATION_PLAN.md) supplied instead. |
| 7 | Independent application test image pack | **Unavailable:** 0 qualified REAL and 0 qualified FAKE images. [Status record](demo-pack-status.json). |
| 8 | Per-image prediction CSV | **Control validation CSV supplied**, explicitly not a demo pack: [control-validation-predictions.csv](control-validation-predictions.csv). [Demo CSV template](demo-predictions.TEMPLATE.csv) contains headers only and is not results. |
| 9 | Final integration results | **Unchanged production availability/CORS verified after restoration.** New candidate integration and independent-pack browser/API predictions were not performed. Prior full integration evidence remains separately dated. |
| 10 | Updated README | Updated project README links these outcomes and retains the historical frozen-test results. |
| 11 | Completion report with limitations | This report, the interruption audit, scripts/configuration, local evidence inventory and completion-status record. |

## Application and production protection

The active production model remains:

```text
backend/model/deepfake_model.keras
SHA256: 2c5908debc8a05369adeeeb2d094d595bd981ef84ddc29a42e8f88ae177d7f16
Decision threshold: 0.42
```

The existing candidate remains:

```text
backend/model/candidates/run-20261106-v2/deepfake_model_v2.keras
SHA256: 193739a62d2a282ef3f9959e76511796293608f7fb12c436031cc3f7f0390237
Decision threshold: 0.30225202441215515
```

No model/threshold replacement, label change, threshold search, old frozen-test inference, old-report alteration, gate change, package installation, frontend behavior change or deployment occurred in this follow-up. Production restoration used the existing launch configuration and original files. The HTTP checks did not run predictions or insert/delete history records.

Fresh endpoint evidence: [production-http-checks-restored.json](production-http-checks-restored.json). The earlier availability record remains preserved, as does the intervening failed-connection observation. Historical backend/unit/browser/actual-prediction checks are in the [earlier completion report](../completion-20261110/FINAL_REPORT.md); those suites were **not rerun** in this follow-up.

The historical learning-curve page was rendered locally in Edge; it is not an application integration test. Its first phone capture revealed table-induced overflow, which was corrected in CSS but not re-rendered. The saved phone capture is diagnostic evidence, not a final responsive-layout certificate. Missing matplotlib/default Chromium did not trigger package/browser installation; the existing Edge channel rendered the page.

## Independent data and demonstration filenames

**Exact final demonstration filenames: none.** There are no qualified files in the requested REAL/FAKE pack. No images were downloaded during public source research, and no training, model-selection validation or old frozen-test image was repackaged as independent.

The [independent evaluation plan](INDEPENDENT_EVALUATION_PLAN.md) documents researched sources, their provenance/licensing limitations, a proposed new capture/generation protocol, disjoint demonstration/evaluation allocation, fixed model/threshold lock, and one-shot evaluation. Different hashes alone would not establish independence.

**This work does not independently validate any model for final promotion.** The old candidate's historical REAL-recall gate failure remains unchanged; reproducing high validation recall does not supersede that failure.

## How to launch

The frontend and restored production backend were available at the last recorded check. Do not start duplicates if they are still running. Full exact commands are in [LAUNCH_COMMANDS.md](LAUNCH_COMMANDS.md).

Backend, from Windows PowerShell:

```powershell
wsl.exe -d Ubuntu-24.04
```

Then inside WSL:

```bash
cd /mnt/c/Users/mohda/OneDrive/Desktop/Deepfake-Image-Detection
source /home/mohdaafras/deeptrace-env/tf-gpu/bin/activate
export TF_FORCE_GPU_ALLOW_GROWTH=true
export TF_NUM_INTRAOP_THREADS=4
export TF_NUM_INTEROP_THREADS=1
python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8002
```

Frontend, in a separate Windows PowerShell terminal:

```powershell
Set-Location "C:\Users\mohda\OneDrive\Desktop\Deepfake-Image-Detection\deeptrace-ai---deepfake-image-detection-&-forensics"
npm run dev
```

Check:

```powershell
curl.exe --fail http://127.0.0.1:8002/api/v1/health
```

- Application: http://127.0.0.1:5173
- Swagger: http://127.0.0.1:8002/docs

## Evidence location and next boundary

```text
Project deliverables:
C:\Users\mohda\OneDrive\Desktop\Deepfake-Image-Detection\completion-final\

Preserved experiment:
/home/mohdaafras/deeptrace-experiments/final-model-correction-20261110-001/
```

Do not replay the original evaluation CLI or resume inference into this interrupted output directory. A later experiment needs a new run ID and a reviewed runtime plan. Further fitting needs a concrete training/validation-supported hypothesis; promotion needs valid new independent evidence and **explicit approval for integration**. The immediate submission should state these limitations rather than claim that the detector was corrected or retrained successfully.
