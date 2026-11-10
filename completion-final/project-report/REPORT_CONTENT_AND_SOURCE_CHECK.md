# Report content and source check

## Purpose and scope

Audience: academic mini-project evaluators in Artificial Intelligence and Machine Learning. The report is original DeepTrace AI content following the supplied sample's academic layout. It is not a Neural Style Transfer report and does not claim reinforcement-learning implementation.

Required deliverables:

- `DeepTrace_AI_Project_Report.docx` — editable paragraphs, numbered headings, captions and bordered tables.
- `DeepTrace_AI_Project_Report.pdf` — rendered directly from the final DOCX's paragraphs, tables, image binaries and intended page breaks using a local fallback renderer. Report text was not separately rewritten for the PDF.
- `MISSING_SCREENSHOTS.md` — required/optional image status and unresolved information.
- This source-check record.

Document preparation did not launch the application, load a model, train, infer, evaluate an image, traverse dataset folders, read old-test per-image records or change application source. The previously completed experiments remain closed. Current implementation was reviewed read-only; saved reports supply the historical metrics. Database behavior was verified from schema/service source, without opening or changing the production database.

## Cover verification

| Field | Report content | Evidence |
|---|---|---|
| Institution | P.A. COLLEGE OF ENGINEERING, MANGALORE | User request and sample |
| Title | DEEPTRACE AI — DEEPFAKE IMAGE DETECTION USING DEEP LEARNING | User request |
| Type | Subject Based Mini Project | User request |
| Subject | DEEP LEARNING & REINFORCEMENT LEARNING | User request |
| Department | ARTIFICIAL INTELLIGENCE AND MACHINE LEARNING | User request |
| Student | Mohammed Shazin Afras | User request |
| USN | 4PA23AI035 | User request; square brackets treated as field delimiters |
| Faculty | Dr. Mohammed Zakir Bellary | User request; normal typographic spacing |
| Academic year / submission date | Not invented or printed | Not supplied |
| Emblem | Original embedded 200 × 200 image from sample PDF, xref 9 | SHA256 recorded in asset provenance |

The sample's student name and USN were not reused. Bibliography access dates are research dates, not an invented submission date.

## Required sections

The report contains these numbered main sections in order:

1. Introduction
2. Objectives
3. System Architecture
4. Dataset Used
5. Technologies Used
6. Methodology
7. Evaluation Metrics
8. Results
9. Conclusion
10. Future Scope
11. References

## Source map

Paths below are relative to the project root. Line ranges refer to inspected source, not a claim that the code was executed during report preparation.

| Report claim | Source and relevant lines | Qualification |
|---|---|---|
| FastAPI startup initializes database and model | `backend/main.py:13–36` | Configuration addresses do not establish current availability. |
| Prediction route, multipart field, threadpool and persistence | `backend/app/routes/prediction.py:15–45` | Grad-CAM is included with prediction, not a separate endpoint. |
| Lock, score rule, timing and Grad-CAM diagnostic | `backend/app/services/prediction_service.py:15–53` | Timing includes lock wait, preprocessing and explanation; excludes decoding/storage/network. |
| Defaults and model loader checks | `backend/app/config.py:6–25`; `backend/app/services/model_loader.py:23–52` | Loader checks shapes/sigmoid, not model SHA256 or an EfficientNet-specific architecture contract. |
| Production threshold = 0.42 | `backend/model/threshold.json:1`; saved final-completion model record | No threshold change. |
| Pillow RGB → float32 → bilinear 224×224, antialias=False | `backend/app/services/preprocessing.py:7–16` | No external /255, EXIF transpose, face crop or aspect-preserving model padding. |
| JPEG/PNG/WebP, frame/pixel validation, upload limit | `backend/app/utils/image_utils.py:8–39`; `backend/app/routes/prediction.py:31–45` | 10 MiB byte check follows multipart parsing. |
| EfficientNetB0, pooling, dropout 0.3, sigmoid | `README.md:47–59`; `completion-final/TRAINING_AUDIT.md:24–31` | Recorded prior model inspection; no model imported or executed for this report. |
| Last Conv2D, class-specific target, gradient-weighted map | `backend/app/services/gradcam_service.py:12–67` | Relative attention, not manipulation segmentation or probability. |
| OpenCV use; pale-to-dark blue; 60/40 overlay | `backend/app/services/gradcam_service.py:70–96` | OpenCV is used for visualization, not model RGB decoding/resizing. |
| SQLite metadata schema and threshold migration | `backend/app/database.py:9–29`; `backend/app/schemas.py:22–37` | No image pixels or Grad-CAM persisted. Old threshold values remain nullable. |
| Metadata history list/detail/delete | `backend/app/services/history_service.py:5–34`; `backend/app/routes/history.py:9–33` | Browser pagination is not server pagination. |
| Health response | `backend/app/routes/health.py:10–16` | Readiness is expressed in response body. |
| Upload/preview/abort/UI states | frontend `src/pages/DetectionPage.tsx:21–85` | Aborting the browser wait need not cancel backend processing. |
| FormData/fetch, server labels, API origin | frontend `src/services/api.ts:3–11,60–75,121–176` | Intended local origin is configurable, not an enforced local-only restriction. |
| History UX and exports | frontend `src/pages/HistoryPage.tsx:26–80` | Model predictions in history are not ground-truth classifications. |
| Result and image views | frontend `src/components/detection/AnalysisResults.tsx:9–30`; `GradCamViewer.tsx:9–32` | Visualizations can be unavailable. |
| Declared frontend stack | frontend `package.json:6–32` | React 19/Vite 8/Tailwind 4 are declared major versions, not freshly measured installed versions. |
| Recorded validation environment | `completion-final/VALIDATION_REPORT.md:7–16` | WSL runtime; not identical to every Windows environment. |
| Dataset counts, duplicates, metadata, provenance limitations | `completion-final/TRAINING_AUDIT.md:19–25,35–38` | Audit findings copied; no fresh folder scan or decode. |
| Historical fitting, weighting, augmentation, selection and recovery | `completion-final/TRAINING_AUDIT.md:27–35` | No new fitting history created. Exact RNG/next-batch continuity not guaranteed. |
| No demonstrated training correction | `completion-final/TRAINING_AUDIT.md:38–57` | Generalization explanations remain hypotheses, not proven causes. |
| Historical test aggregates | `completion-20261110/FINAL_REPORT.md:40–80` | Already evaluated set; no new test inference, scores or IDs accessed. |
| REAL-recall gate failure | `completion-20261110/FINAL_REPORT.md:128–144` | Six gates passed; REAL recall 78.7179% failed ≥80%; no promotion. |
| Reused control-validation values and confusion matrix | `completion-final/VALIDATION_REPORT.md:18–48` | Existing candidate only, not independent test or production metrics. |
| Interrupted alternatives and no approval | `completion-final/VALIDATION_REPORT.md:50–86`; `FINAL_COMPLETION_REPORT.md:49–59,77–107` | No partial comparison used to select a candidate. |
| Later runtime terminations | `completion-final/POST_COMPLETION_RUNTIME_UPDATE.md:3–23` | Saved point-in-time results remain historical; no report-time restart. |

Frontend base: `deeptrace-ai---deepfake-image-detection-&-forensics/`.

## Metric transcription checks

### Historical aggregate evidence only

| Metric | Production | Existing candidate |
|---|---:|---:|
| Accuracy | 69.8854% | 86.9051% |
| Balanced accuracy | 69.7831% | 86.8462% |
| FAKE recall | 83.9039% | 94.9745% |
| REAL recall | 55.6623% | 78.7179% |
| Macro F1 | 0.692271 | 0.868039 |
| ROC AUC, REAL-positive | 0.8008827714 | 0.9580996775 |

The metrics were transcribed from the saved human-readable completion report. No predictions were regenerated and no old-test per-image records were used.

### Reused candidate validation

39,044 records at threshold 0.30225202441215515. Accuracy 96.7601%; balanced accuracy 96.7624%; REAL precision/recall 96.3698%/97.1396%; FAKE precision/recall 97.1518%/96.3851%; macro F1 0.967601 (rounded); ROC AUC 0.9954448744; Brier 0.02623040588; 10-bin ECE 0.01499982960. Matrix `[[18931,710],[555,18848]]`, actual rows/predicted columns in FAKE, REAL order.

These values are explicitly described as reused validation. The report never calls 96.76% independent test accuracy and never says the final correction work trained or approved an improved model. No calibration transformation was fitted.

### Exact uploaded screenshot values

- FAKE: confidence **89.4%**; REAL **10.6% / 0.1063**; FAKE **89.4% / 0.8937**; threshold **0.42**; displayed latency **0.795 s**.
- REAL: confidence **84.2%**; REAL **84.2% / 0.8419**; FAKE **15.8% / 0.1581**; threshold **0.42**; displayed latency **0.798 s**.

Labels are model outputs, not independently authenticated truth. The optional earlier misclassification record is not used, avoiding any need to inspect the referenced image.

## Figures and tables

- Fig 1: System Architecture of the DeepTrace AI System — original diagram drawn from verified source flow.
- Fig 2: FAKE Image Detection Result with Grad-CAM Visualization — exact uploaded screenshot.
- Fig 3: REAL Image Detection Result with Grad-CAM Visualization — exact uploaded screenshot.
- Fig 4: DeepTrace AI Dashboard — Historical Browser-Test Capture — existing genuine UI evidence, explicitly qualified.
- Nine editable bordered tables cover endpoints, dataset counts, technologies, historical fitting, metric definitions, historical metrics, validation and screenshot values.

No heatmap, overlay, model result card, dataset example or score was synthesized to improve the appearance of results. All figures retain aspect ratio. The source image hashes are in `asset-provenance.json`.

## Bibliographic verification

Verified online during document research:

- Tan and Le, EfficientNet, ICML/PMLR 97, 6105–6114 (2019): `https://proceedings.mlr.press/v97/tan19a.html`.
- Selvaraju et al., Grad-CAM: author/title verified at `https://arxiv.org/abs/1610.02391`. ICCV 2017 version cited; the later journal version is not confused with the conference date.
- Rössler et al., FaceForensics++: author/title verified at `https://arxiv.org/abs/1901.08971`. Related-work citation only.
- Official TensorFlow Keras, Keras EfficientNet, FastAPI and React documentation.

The CVF publisher pages returned HTTP 403 to the fetch tool; arXiv records supplied the author/title verification instead. An OpenCV documentation fetch also returned 403; OpenCV usage is verified directly from local source, and that failed fetch is not presented as a verified bibliography source. No fabricated DOI, dataset attribution or paper title was added.

## Tooling and reproducibility

Existing Python environments checked did not contain the required DOCX/PDF libraries. A separate `.doc-tools` virtual environment was created inside this report directory with `python-docx==1.2.0` and `PyMuPDF==1.26.5` and their dependencies. After Word export stalled, `reportlab==4.4.4` and its dependencies were added to that same isolated environment. No application environment packages were installed, upgraded or removed, and no office suite was installed.

The installed Microsoft Word opened the report, but PDF export stalled in the initial attempt and two controlled variants (unsynced local copy and modern document compatibility). A one-paragraph diagnostic also stalled in PDF export. No Word-export success or established root cause is claimed. Only the report-created Word instances were stopped; the pre-existing Word document was left open. The final PDF was instead rendered directly from the final DOCX using `render_docx_pdf.py`. All final page scale factors are 1.0: no page-wide shrinking was required after compacting the architecture diagram.

**Conversion limitation:** the PDF and DOCX have verified matching text and image content, but a native Word page-by-page rendering could not be certified. Word may paginate or wrap slightly differently. The 12-page PDF is the visually checked print version; the DOCX remains editable with intended page/section breaks and PAGE fields.

Build sources: `prepare_report_assets.py`, `build_report.py`, `render_docx_pdf.py`, `verify_report.py`. The unsuccessful Word-export scripts are retained for transparency, not as a required final build step. Rebuilding is document-only; review output-overwrite behavior before running it on a later edited report. The final DOCX remains directly editable without any script.

An initial Git Bash Python alias resolved to the Microsoft Store stub and failed before creating the directory; an explicit installed interpreter was used. The first asset-preparation attempt encountered a bytes-to-JSON serialization issue in PDF placement metadata; it was corrected without altering input screenshots or the sample PDF.

## Final layout and integrity verification

Final automated verification completed successfully after correcting console-only Unicode output in the checker. The JSON evidence was written correctly even in that initial console-output failure; the final full checker run exited successfully.

| Check | Final result |
|---|---|
| Required files | All four requested deliverables present |
| PDF pagination | 12 pages: unnumbered cover + body pages 1–11 |
| Page orientation | Portrait, except physical pages 8 and 9 for full-width FAKE/REAL screenshots |
| Main sections | All 11, in the required order |
| Cover identity | Correct institution, title, course, department, student, USN and faculty; no invented year/date |
| Editable DOCX | 252 non-empty paragraph/cell text units, 9 native tables, 5 inline images |
| Text agreement | Every non-empty DOCX paragraph/cell matched PDF text after layout-whitespace normalization; zero unmatched units |
| Required figure captions | Fig 1, Fig 2 and Fig 3 present verbatim; genuine dashboard caption also present |
| Screenshot binaries | Exact uploaded FAKE/REAL and saved dashboard binaries embedded in DOCX; no crop operations |
| PDF screenshot pixels | Extracted FAKE, REAL and dashboard images have identical dimensions and RGB pixels to source images |
| Figure proportions | Original aspect ratios preserved |
| PDF layout | All pages rendered and visually inspected; no observed overlap, page-edge clipping or accidental blank page |
| Fonts / tables | Embedded Times New Roman PDF fonts; serif justified body; bordered tables and centered captions |
| Metric honesty | Historical test separate from reused validation; failed REAL-recall gate retained; no independent-evaluation or new-training claim |
| Source protection | All 25 explicitly allowlisted input hashes unchanged, including production model and threshold |
| Prohibited execution | No training, inference, dataset traversal, old-test per-image access, source changes or service restart |
| Native Word pagination | Not certified because Word PDF export stalled even on a minimal diagnostic; final PDF is the checked print layout |

### Page-by-page visual review

| Physical page | Reviewed content | Outcome |
|---|---|---|
| 1 | Bordered cover, supplied emblem and identity | Readable; correct details; no invented year/date |
| 2 | Introduction and objectives | Justified prose and numbered objectives; no clipping |
| 3 | Architecture, caption, endpoint table | Arrow labels and database branch visible; compact final diagram re-rendered and re-inspected |
| 4 | Dataset and technology tables | Counts, column widths and borders legible |
| 5 | Methodology and historical training | Table rows remain readable; no cut-off text |
| 6 | Decision rule, Grad-CAM, history and metric definitions | All formulas/qualifications visible |
| 7 | Historical test and reused-validation results | Distinct contexts, thresholds and failed gate clearly visible |
| 8 | Exact FAKE result and editable value table | Full source screenshot; all three panels retained; scores match |
| 9 | Exact REAL result and editable value table | Full source screenshot; all three panels retained; scores match |
| 10 | Historical dashboard | Full screenshot; disposable-database and runtime limitations visible |
| 11 | Conclusion and future scope | Honest non-promotion outcome and actionable future work |
| 12 | References | Full bibliography; URLs and provenance note fit |

The first review covered all 12 rendered pages. Only the architecture figure/layout changed afterward; its final page was separately rendered and inspected again. All other page content/layout was unchanged by that last build. Final automated checks were rerun across the entire PDF.

Evidence: `quality-check.json`, `pdf-renderer.json`, `pdf-page-renders/`, `pdf-extracted-text.txt`, `source-integrity-before.json`, `source-integrity-after.json`, and `asset-provenance.json`.

Final report hashes:

- DOCX SHA256: `0d45da6051821d90f62498d8a9bf5bafbca16e762ad9d47ba4d333e6537b1791`
- PDF SHA256: `996888a19bd7607de25391d8eefa41a4f7af5e70b6d974935e324067f5f752da`

Unresolved scientific/report limitations are explicit, not hidden: incomplete dataset provenance, no new independent evaluation, no newly trained/approved improvement, optional upload/history screenshots unavailable, and unverified native Word pagination. None prevents reading or editing the delivered report; the checked PDF provides the final print layout.
