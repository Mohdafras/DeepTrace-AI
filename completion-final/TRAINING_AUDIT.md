# Training-pipeline audit and fitting decision

## Scope and evidence

This new request starts from the completed detailed train/validation audit rather than repeating a broad dataset scan. The new Phase A preparation **rehashed 105 protected/inspected artifacts and found all unchanged**. It also bound the prior audit's completion records and corrected report hashes, materialized train-only and validation-only manifests, and staged seven distinct model-file copies outside the production/candidate directories.

The detailed audit and source citations are copied into the experiment's `evidence/prior-audit.json` and `evidence/prior-findings.md`. New preparation evidence is `reports/phase-a-audit.json` and `evidence/protected-before.json` under:

```text
/home/mohdaafras/deeptrace-experiments/final-model-correction-20261110-001/
```

The prior audit read all **179,430 raw train/validation files twice as opaque bytes**, checking 1,686,853,586 bytes per pass with zero hash discrepancies. That was a previous completed step, not a repeated image audit in this new preparation. New validation workers verify bytes and decode only their locked validation inputs. No old frozen-test image is an allowed decoder input.

## Findings

| Area | Verified evidence | Decision / limit |
|---|---|---|
| Effective training counts | FAKE 69,996; REAL 53,255; total 123,251 | Moderately imbalanced, approximately 56.79% / 43.21%. Do not replace the audited manifest with raw folders. |
| Effective validation counts | FAKE 19,641; REAL 19,403; total 39,044 | Near-balanced. Validation remains for selection only, never fitting. |
| Raw data and exclusions | Raw Train: 70,001 per class. Raw Validation: 19,641 FAKE and 19,787 REAL. Existing exclusions: 5 train FAKE, 16,746 train REAL, 384 validation REAL. | Exclusions were not modified. |
| Exact duplicates | Raw within-train groups 11,417; within-validation 384; cross train/validation 5,334. Effective manifest: zero within/cross exact encoded- or recorded-pixel-hash groups. | Raw-folder leakage exists; effective exact-hash leakage is not demonstrated. Identity, near-duplicate and source-video separation remain unknown. |
| Labels | Manifest/training contract Fake=0, Real=1. Single sigmoid is pReal. | No discovered mapping inversion. Folder labels are not independently authenticated image provenance. |
| Preprocessing | Pillow RGB conversion, float32 0–255, TensorFlow bilinear 224×224 resize, antialias=False; no external /255; EfficientNet internal scaling retained. No EXIF transpose. | No audited-source RGB/BGR, normalization or train/serve resize mismatch identified. Non-square uploads stretch. |
| Stored image metadata | Historical inspection records train/validation files as single-frame 256×256 RGB JPEGs; both later byte passes matched those records. | No corruption indicated by the existing checks. The new preparation did not repeat image decoding. |
| Model | EfficientNetB0 + global average pooling + dropout 0.3 + one sigmoid. | REAL iff pReal >= the configured threshold; pFake=1-pReal. Never invert outputs to improve apparent accuracy. |
| Class weighting | Inverse-frequency weights already applied in both fit stages: FAKE 0.8804145951, REAL 1.1571777298. | Adding the same weighting again is not a demonstrated correction. No balanced batch sampler is present. |
| Augmentation | Training-only horizontal flip, ±0.02-turn rotation with bilinear/reflected borders; dropout 0.3. Identical policy for both labels. | Rotation factor describes magnitude, not a 2% application probability. No new augmentation is justified by old-test errors. Validation/inference uses training=False. |
| Head fitting | Frozen ImageNet backbone, Adam LR 0.001; 3 of at most 5 epochs completed. | Existing early stopping and LR reduction are present. |
| Fine-tuning | block6*, block7*, top_conv and classifier trainable; all BatchNormalization frozen; new Adam at LR 1e-5; 7 of at most 8 epochs completed. | Backbone training=False keeps BN behavior fixed without preventing trainable convolution gradients. |
| Checkpoint control | Minimum validation-loss checkpoint selected fine epoch 4. Actual candidate bytes equal best_fine.keras. Separate archived epoch-4 bytes differ. | Use the actual candidate as control. Do not infer learned-weight differences or equivalence from archive serialization hashes. |
| Stopping/LR policy | EarlyStopping patience 2 head / 3 fine; ReduceLROnPlateau factor 0.5, patience 1, minimum LR 1e-7; completed-epoch archives retained. | No missing callback bug to repair. Logged epoch-end LR may already include a callback reduction. |
| Fitting trend | Fine training loss falls from 0.18007 to 0.04240. Validation loss reaches 0.09727 at epoch 4, then 0.10324, 0.10366, 0.09758. | Some late fitting without consistent validation-loss improvement. Training loss is weighted/augmented and not directly identical in meaning to validation loss. |
| Recovery | A recorded file-lock failure led to interrupted-epoch replay with restored optimizer/callback state; exact next-batch/RNG continuity was explicitly not guaranteed. | Recovery effects on generalization remain unverified. Stale running_stage bookkeeping does not establish corrupted weights. |
| Selection reuse | Same validation set used for stage/checkpoint and a 30,442-threshold search in the existing run. | Selection optimism is plausible; its size is unknown. Any new checkpoint comparison adds further reuse and is not independent evidence. |
| Calibration | Sigmoid scores are raw model outputs. | New workers calculate validation Brier score, log loss and 10-bin reliability/ECE diagnostics; they do not fit calibration or change thresholds. |

**No causal explanation of the generalization gap has been established.** Missing source/identity metadata, distribution shift, label noise, diversity limitations, augmentation effects and recovery behavior remain hypotheses, not proven fixes.

## Decision: no additional fitting in this experiment

The audit does not support claiming that label inversion, missing class weights, extra normalization, unfrozen BatchNormalization or absent early stopping caused the failure. Those presumed bugs should not be introduced or “fixed” without evidence. More epochs could increase the late fitting already visible in the logs.

Therefore this run is a **validation-only checkpoint-selection comparison**, not retraining. No new training history or newly fitted weights will be represented as produced by it. The existing training implementation/configuration remain unchanged. The new executable deliverables are the preparation, guarded validation runner, metric checks, and locked experiment configuration; a new fitting script is intentionally not supplied as if an audit-supported training correction had been found.

### Locked comparison protocol

1. Actual existing candidate control first; fixed threshold **0.30225202441215515**.
2. Same 39,044 validation records, order, byte hashes, preprocessing, float32 input and batch size 4.
3. Require exact reproduction of the saved control confusion matrix. On mismatch, stop; do not adjust threshold, retry with a different device or run alternatives to hide the discrepancy.
4. Only after control succeeds: one pass each for archived fine epochs **1, 2, 3, 5, 6, 7**. Never substitute the separately saved epoch-4 archive.
5. Eligible alternatives cannot reduce either class's validation recall relative to the reproduced control. Rank by balanced accuracy, then REAL recall, then earlier epoch.
6. A meaningful validation improvement requires balanced accuracy **+0.002 absolute**, REAL recall **+0.002 absolute**, and no FAKE-recall decrease. These are selection-experiment criteria, not replacements for any original promotion gate.
7. Run one isolated worker at a time, with 3,584 MiB TensorFlow GPU allocation limit, at least 512 MiB observed GPU free, at least 2 GiB available RAM, a 3.5 GiB worker RSS guard and a one-hour worker timeout. Monitor every five seconds. These are practical stopping guards, not an OS-level guarantee against every possible crash.
8. Retain all outputs, including failure records. Reverify protected originals at completion. Never write to production model/threshold or old experiments.

**Execution outcome:** the control completed and reproduced its saved validation results exactly. WSL then stopped during the first alternative; the comparison remained incomplete, so no meaningful-improvement decision or new candidate export was made. Protected hashes were reverified after the interruption. See [VALIDATION_REPORT.md](VALIDATION_REPORT.md) and [FINAL_COMPLETION_REPORT.md](FINAL_COMPLETION_REPORT.md). **Independent promotion remains blocked without valid new untouched evaluation data and explicit integration approval.**

## Curves and application scope

- [Historical interactive learning curves](historical-training-curves.html)
- [Full-precision historical CSV table](historical-training-table.csv)
- [New independently sourced data plan](INDEPENDENT_EVALUATION_PLAN.md)
- [Exact launch commands](LAUNCH_COMMANDS.md)

The curve source CSVs are historical, verified copies. No new fitting was executed to make those charts. The existing production application's endpoint availability/CORS checks are recorded separately; they are not a new candidate integration test or classification-accuracy result.
