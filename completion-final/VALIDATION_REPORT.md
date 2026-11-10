# Validation report: control completed, comparison interrupted

**Overall experiment status: INCOMPLETE. No checkpoint-selection decision or new candidate export was made.**

The existing candidate control completed one fresh validation pass. WSL subsequently stopped while fine epoch 1 was being evaluated, terminating the supervisor and production backend without the normal finalization record. No inference was retried after the interruption.

## Verified completed control

- Model: existing `run-20261106-v2/deepfake_model_v2.keras`, loaded from a separate read-only staged copy.
- SHA256: `193739a62d2a282ef3f9959e76511796293608f7fb12c436031cc3f7f0390237`.
- Input: **39,044 reused validation images**, 19,641 FAKE and 19,403 REAL.
- Fixed threshold: **0.30225202441215515**. REAL iff pReal >= threshold; pFake = 1 − pReal.
- Completion: **2026-11-10 06:17:33 UTC**.
- Scoring/metric duration: 1,883.35 seconds; supervised worker duration including startup: 1,892.05 seconds.
- Runtime: Python 3.12.3, TensorFlow 2.19.1, Keras 3.15.1, NumPy 2.1.3, Pillow 13.0.0; RTX 3050; batch size 4.
- After WSL reopened, every completed control prediction's membership, order, hash, label, complement, threshold and class decision was verified. Pure metrics were recomputed from the saved CSV and matched exactly. No images were reopened for that recomputation.

| Control validation metric | Result |
|---|---:|
| Accuracy | 96.7601% |
| Balanced accuracy | 96.7624% |
| REAL precision | 96.3698% |
| REAL recall | 97.1396% |
| FAKE precision | 97.1518% |
| FAKE recall | 96.3851% |
| Macro F1 | 96.7601% |
| ROC AUC, REAL-positive | 0.9954448744 |
| REAL→FAKE rate | 2.8604% |
| FAKE→REAL rate | 3.6149% |

Confusion matrix, **actual rows / predicted columns**, order **FAKE, REAL**:

| Actual / predicted | FAKE | REAL |
|---|---:|---:|
| FAKE | 18,931 | 710 |
| REAL | 555 | 18,848 |

This reproduces the saved control matrix exactly. Accuracy, balanced accuracy, both recalls, ROC AUC and Brier score all have zero recorded difference from the saved validation result. This is reproduction of a known validation result—not a new improvement and not independent test performance.

### Calibration diagnostics

| Diagnostic | Result |
|---|---:|
| Brier score, REAL target | 0.02623040588 |
| Binary log loss, clipped at 1e-7 | 0.09724665680 |
| ECE, 10 equal-width pReal bins | 0.01499982960 |

Reliability-bin counts and observed REAL fractions are preserved in [control-validation-calibration.json](control-validation-calibration.json). Bins include pReal=1 in the last interval. ECE is approximately 1.50 percentage points on this **reused validation distribution**. It is bin-dependent and is not a certificate of calibration on new sources. No calibration transformation was fitted. The UI's raw sigmoid outputs must not be described as calibrated certainty.

## Incomplete alternatives

| Checkpoint | Execution status | Eligible for selection from this run? |
|---|---|---|
| Actual candidate control | Completed and verified, 39,044 records | Baseline only |
| Fine epoch 1 | Interrupted; no completion marker | No |
| Fine epochs 2, 3, 5, 6, 7 | Not started | No |

The partial fine-01 CSV contains 6,141 parseable data rows, while the last progress log reports 6,000/39,044. Its tail and partial membership were not certified as a complete evaluation. **No partial accuracy was calculated or used for selection.** The CSV, stdout, stderr and resource log remain preserved in the experiment directory.

The planned seven-pass comparison did not finish. The locked meaningful-improvement rules were neither relaxed nor evaluated on partial results. The prepared `finalize_comparison.py` was **not executed**; it requires a complete successful supervisor record and cannot finalize this interrupted run as a success.

## Interruption and resources

The last fine-01 resource sample is **2026-11-10 06:22:40 UTC**. The exact time and cause of WSL stopping are unknown. Later checks found no running WSL distributions and a refused connection to backend port 8002; the Windows frontend still returned HTTP 200. A query for recent System-log critical/error/warning events returned no matching records. The retained worker stderr contains TensorFlow registration notices and successful GPU initialization, but no terminal exception explaining the WSL stop.

| Sampled observation | Control | Partial fine-01 |
|---|---:|---:|
| Resource observations | 372 | 61 |
| Maximum whole-device GPU used | 4,024 MiB | 4,024 MiB |
| Minimum GPU free | 1,979 MiB | 1,979 MiB |
| Minimum available RAM | 5,490,790,400 bytes | 5,532,950,528 bytes |
| Maximum observed worker RSS | 1,418,817,536 bytes | 1,418,010,624 bytes |

TensorFlow confirmed the configured **3,584 MiB allocation limit**. Whole-device GPU use also includes context/driver allocations and the production backend; it is not the worker's TensorFlow allocator alone. The last retained samples do not show the configured low-memory guard being reached. They also cannot exclude a later transient or establish that OOM, manual shutdown, host suspension or another cause was responsible. Monitoring did not prevent the interruption, and no crash-prevention guarantee is claimed.

## Integrity and decision

After reopening WSL for evidence inspection:

- All **106 protected/inspected original file hashes** matched their baselines: the initial 105 plus the pure-metric source file.
- All seven staged model-file hashes, the experiment configuration, worker source lock, supervisor source lock and validation manifest matched.
- The control's prediction, metric and calibration files matched their completion hashes; its 39,044 predictions and metrics were verified again without inference.
- No original model, threshold, prior report, promotion gate or dataset was modified by this experiment.
- No new fitting, candidate export, model-selection decision, independent evaluation or promotion occurred.

**Decision: preserve production.** The completed control does not repair the prior candidate's independent-test gate failure. An interrupted comparison and missing independent data do not justify promotion.

## Evidence

- [Control per-image validation predictions](control-validation-predictions.csv) — **not a demo or independent test pack**.
- [Control metrics and uncertainty intervals](control-validation-metrics.json).
- [Control completion and exact reproduction deltas](control-validation-complete.json).
- [Post-interruption audit and resource observations](interruption-audit.json).
- [Locked configuration](experiment-config.json).
- [Independent evaluation acquisition plan](INDEPENDENT_EVALUATION_PLAN.md).

Full experimental sources, train/validation-only manifests, staged checkpoints and logs remain under:

```text
/home/mohdaafras/deeptrace-experiments/final-model-correction-20261110-001/
```

Do not resume or replay inference into this run. Any later attempt requires a new output/run ID, reviewed runtime plan and unchanged scientific rules; the old frozen test remains excluded.
