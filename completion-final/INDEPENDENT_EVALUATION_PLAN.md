# Independent evaluation and demonstration plan

**Status: NOT EXECUTED — no independently qualified image pack is available.**

No new evaluation accuracy, independent ground-truth labels, demonstration filenames or application predictions are claimed. No external images/archives were downloaded during the source research. The old frozen test set is already observed and remains excluded from further model selection and evaluation. Its images, image IDs and error records were not consulted for this plan.

## Public sources investigated

| Proposed role | Source and stable reference | Supporting documentation | Why not accepted as an independent pack |
|---|---|---|---|
| Photographic-origin REAL portraits | Face Research Lab London Set, DOI **10.6084/m9.figshare.5047666.v5**; [publisher metadata](https://api.figshare.com/v2/articles/5047666/versions/5) | The publisher documents photographs of 102 adults captured in London in April 2012, consent for specified research uses, 1,350 × 1,350 images and downloadable archives such as neutral_front.zip. Metadata lists CC BY 4.0. | No individual image was acquired or examined. The reviewed record does not establish an unbroken camera-original chain or complete processing history. Historical reuse in this project's training sources is unresolved. Licensing, consent scope and redistribution permission must be checked before distribution. |
| Fully synthetic FAKE portraits | [SFHQ-T2I](https://www.kaggle.com/datasets/selfishgene/sfhq-t2i-synthetic-faces-from-text-2-image-models), Kaggle dataset 5817893 version 1, created 2024-10-04; [dataset metadata](https://www.kaggle.com/api/v1/datasets/view/selfishgene/sfhq-t2i-synthetic-faces-from-text-2-image-models) | Documentation describes 122,726 synthetic portraits from FLUX.1 variants, SDXL and DALL-E 3. [Generator code pinned at a8064474a09cbcec27a498f5bf51ad08298ba47c](https://github.com/SelfishGene/SFHQ-T2I-dataset/blob/a8064474a09cbcec27a498f5bf51ad08298ba47c/create_face_dataset.py) uses text-to-image requests and records filenames, model names, prompts and configurations. Dataset metadata labels the license MIT. | No images or CSV records were downloaded or checked. The code does not establish per-output timestamps, resolved model revisions, request IDs, output hashes or provider-confirmed seeds. Requested settings are not proof of reproducibility. Archive retrieval/authentication and complete licensing terms were not tested. Historical overlap with this detector's data is unresolved. |

Source research establishes candidates for acquisition, not verified individual labels or disjointness. Different filenames, repositories and encoded hashes do not rule out crops, resizing, recompression, related identities or reuse of the same source photograph. The publicly listed sources predate the current 2026 training run and cannot be described as post-training.

## Preferred new collection

1. **Lock the detector before evaluation.** Freeze its model SHA256, threshold file SHA256, preprocessing code/version and inference runtime. Preserve the approved train/validation manifests. Do not change any of the existing promotion rules.
2. **Acquire documented new photographs.** Use consenting participants and new capture sessions after the detector freeze. Preserve original camera files, capture/session records, consent and permissions for the intended academic demonstration. Preserve every transformation into API-supported derivatives. Authenticity must be supported by this record, not the model's score. Keep sensitive identity/consent records private.
3. **Acquire documented new synthetic images.** Use text-only generation, without reference photographs, and retain the actual model/checkpoint identifier, prompts, seeds where available, effective settings, timestamps, job/request IDs, original outputs and applicable license/terms. Do not fabricate images by relabeling photographs. Fully generated faces test a different task from face swaps; state the evaluated scope explicitly.
4. **Split before scoring.** Reserve at least **20 REAL + 20 FAKE** as the demonstration pack. Independently allocate a separate evaluation set, with distinct capture identities/sessions and unrelated synthetic generation groups. The demo pack is not also the evaluation set. Do not inspect detector predictions to select attractive examples.
5. **Predeclare evaluation size and sampling.** A reasonable planning starting point is 200 images per class across multiple documented sources/generator groups; conduct a precision/power calculation before collection and freeze the actual design. Forty demo images alone cannot establish deployment accuracy. At recall near 80%, 200 independent examples per class still have roughly ±5–6 percentage-point uncertainty, before accounting for source/identity clustering. Do not represent this proposed sample size as collected data or as a changed gate.
6. **Check provenance and allowed-data overlap.** Check new data against approved train/validation metadata only. Use source lineage, transformation history, identity/session separation and near-duplicate methods in addition to exact SHA256. No old-test image, ID, score or error may be used. New capture/generation timestamps help establish image-level disjointness; they do not alone prove identity or distribution independence. If lineage remains unresolved, report that qualification explicitly.
7. **Freeze the new evaluation manifest.** Store source references, provenance records, class-label justification, hashes, dimensions, group IDs, permitted usage and exclusion reasons. Hash and lock it before any evaluation. An independent custodian should hold this set apart from model-selection work.
8. **Run a single paired evaluation after finalization.** Score the fixed candidate and unchanged production model once on the same new manifest, with fixed thresholds. Preserve all results. Report confusion matrices, both-class precision/recall/F1, macro F1, accuracy, balanced accuracy, REAL-positive ROC AUC, error rates and uncertainty, including clustered uncertainty when appropriate. Apply the unchanged promotion-gate definitions to the new evidence; the old gate result does not transfer to a newly selected model. No threshold search or checkpoint choice on these images.
9. **Stop on failure.** A failed gate is not permission to retune and test the same images again. Keep production unchanged. Further model development requires new training/validation work and a genuinely untouched evaluation set.
10. **Integration requires explicit approval.** Only after required checks pass and approval is given should an approved candidate be wired into an isolated application configuration. Do not overwrite original production files. Run the separate demo pack through the actual browser/API request-response flow and preserve every prediction, including errors.

## Demonstration pack acceptance checklist

- At least 20 independently documented REAL and 20 independently documented FAKE files.
- No training, model-selection validation, old frozen-test or new evaluation images.
- Unique image hashes, validated JPEG/PNG/WEBP bytes, single-frame images and dimensions within the API's limits.
- Documented class labels, source records and permissions; no labels inferred from predictions.
- Manifest frozen before any demonstration prediction; no score-based cherry-picking.
- Fixed active-model and threshold hashes recorded with every run.
- Every response retained, including failures. Error responses must not silently disappear from accuracy denominators.
- CSV columns: `filename,ground_truth,source,source_reference,SHA256,image_dimensions,predicted_class,real_probability,fake_probability,correct_or_incorrect`.
- Expected destinations after legitimate acquisition: `completion-final/test-images/real/` and `completion-final/test-images/fake/`.

**Current exact filenames: none.** The destinations have not been populated, and no completed prediction CSV exists. `demo-predictions.TEMPLATE.csv` is an empty schema template, not an experimental result. This work does **not** independently validate a model for final promotion.
