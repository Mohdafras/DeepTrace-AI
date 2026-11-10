# DeepTrace AI — audit and completion record

## Scope and architecture

Inspection covers project-owned backend source/tests/configuration, frontend source/configuration, and model/data/training asset inventory. Generated Python environments, caches and dependency lockfiles are inventoried rather than reviewed as application source. The existing architecture is retained:

- `backend/`: FastAPI routes → Pillow validation → RGB TensorFlow resize → saved Keras model → Grad-CAM → SQLite metadata.
- `deeptrace-ai---deepfake-image-detection-&-forensics/`: existing React/TypeScript Vite frontend, components and styling.
- `backend/model/`: original trained model and threshold; neither is to be rewritten.
- Uploaded image content is not intentionally stored; history stores metadata only.

## Confirmed issues before changes

1. Frontend ignores `predicted_class` and `confidence_score`, recomputing the label at 0.50 instead of trusting the configured backend threshold (0.42).
2. Frontend history parser ignores the API's `{items,total}` shape.
3. Health display does not reliably represent model availability.
4. Mobile sidebar overlaps content, analysis reset is incomplete, and preview object URLs have lifetime issues.
5. Backend preprocessing is defined twice. The effective definition uses TensorFlow bilinear resize, RGB, float32 0–255. Preserve its numerical behavior; remove only the shadowed implementation.
6. Grad-CAM returns only an overlay and silently discards diagnostic exceptions. Subsequent actual-model inspection confirmed the original graph method works; a missing-gradient failure was not reproduced.
7. Backend inference blocks an async request handler. Processing time excludes Grad-CAM.
8. Image validation checks filename extension but not decoded image format or a practical pixel limit.
9. Model loading suppresses startup diagnostics and does not validate the input/output contract.
10. History does not retain the threshold used. Existing timestamps are UTC without an explicit timezone.
11. Baseline tests report **5 passed**, but TestClient does not enter lifespan and the model test silently returns when unloaded. This does not demonstrate working inference.
12. No root startup/readme/ignore guidance. Another project's frontend already occupies port 3000; use port 5173 without terminating that project.

## Phases

- [x] Read-only source/configuration audit and runtime inventory.
- [x] Actual model graph / dataset / training evidence inspection (dataset/notebook absent).
- [x] Backend correctness, validation, diagnostics and Grad-CAM fixes.
- [x] Frontend API integration and responsive workflow fixes.
- [x] Backend isolated tests and real-model inference smoke tests.
- [x] Frontend tests/build and browser workflow.
- [x] Reproducible evaluation tooling; genuine evaluation blocked by absent labeled data.
- [x] Documentation, startup commands and final evidence/limitations.

## Guardrails

No training, threshold tuning on test data, model replacement, dataset deletion, hardcoded runtime predictions, or fabricated metrics. Tests use a temporary SQLite database, not the user's saved history. Synthetic smoke images test mechanics only, never accuracy.

## Verification evidence

### Backend and model — verified

- Final combined command: `backend/.venv/Scripts/python.exe -m pytest backend/tests -q --tb=short` → **67 passed, 1 non-fatal Starlette/httpx deprecation warning, 65.61s** (rerun after the database connection-closing fix).
- These comprise 34 API/preprocessing/Grad-CAM/model/history tests and 33 evaluation-tool tests. No silent model-test return remains.
- A first expanded-test run hit Windows temporary-path issues caused by enormous auto-generated binary fixture IDs. Explicit readable IDs fixed this; the final suite above passed.
- `pip check` → **No broken requirements found**. No Python package upgrades made.
- Real HTTP smoke at `http://127.0.0.1:8003`: prediction 200, CORS for localhost:5173 present, both PNG signatures verified, detail retrieval 200, deletion of its own temporary record 204.
- That synthetic midgray input returned pReal **0.4843948185**, pFake **0.5156051815**, class **REAL**, confidence **0.4843948185**, threshold **0.42**, and no Grad-CAM error. First-request processing time was **4335.83ms** on this machine; not a benchmark or accuracy estimate.
- Port 8003 uses `backend/tests/serve_isolated.py`, the same actual model and a temporary database. The user's port-8002 history was not cleared by testing.
- Startup PowerShell script parsed successfully. Opening its two GUI terminal windows has not been tested; services were started/tested directly instead.
- Model SHA-256 unchanged: `2c5908debc8a05369adeeeb2d094d595bd981ef84ddc29a42e8f88ae177d7f16`.
- Threshold SHA-256 unchanged: `c14467d81bc0323b9464c7418586211248858260bd3a77625b04339d87ca88dd`.

### Model evaluation — blocked, not fabricated

No real dataset, notebook, training log or known-label image collection exists locally. Therefore no genuine Real/Fake-image evaluation, fresh accuracy/precision/recall/F1, false-positive analysis by image, or validation threshold comparison was performed. The evaluation CLI and its synthetic fixture tests work; this is not a trained-model quality result.

The user-supplied matrix totals 10,995 images and implies 69.23% accuracy and a 45.41% real-as-fake rate. These are arithmetic from supplied counts, not rerun results. The supplied dataset count was 10,905; original evaluation provenance is required to reconcile it.

### Frontend — verified

Final verification on 2026-11-05:

| Check | Result |
|---|---|
| `npm test` | **26 passed, 0 failed**, 0.72s |
| `npm run build` | **Passed** strict TypeScript checking and Vite production compilation |
| `npm run test:browser` | **4 passed**, 1.2m, Microsoft Edge |
| `npm ls --depth=0` | All declared frontend dependencies installed; no missing/invalid entries |
| npm lockfile | Root dependency/version/engine declarations match `package.json` |
| Live demo backend | Health reports `model_loaded=true`, threshold 0.42; Swagger returns HTTP 200 |
| Default-endpoint browser smoke | Fresh Edge context on 5173 connects to normal 8002 without an override; health/history succeed, no page/console errors; no history changes |

Browser scenarios:

1. **Desktop (1440×1000):** real uploaded synthetic PNG → actual Keras inference → UI agrees with the server's REAL label despite pReal below 0.50; exact backend confidence retained. Original, distinct heatmap and overlay decode successfully. New Analysis resets; individual detail/deletion and confirmed clear/cancel work. Dashboard reflects real history. No page or console errors in this normal workflow. The chart-data fallback is unclipped in emulated forced colors and print media.
2. **Mobile (390×844):** navigation, unsupported/oversized/corrupt selection errors, actual prediction and all main pages; no horizontal page overflow or uncaught page errors.
3. **Offline/inference errors:** explicit test-only connection failure and HTTP 500 interception; the UI disables unavailable analysis and displays errors without inventing predictions.
4. **Grad-CAM unavailable:** fetches an actual model prediction, then removes only its visualization fields in test interception. The real prediction and original preview remain visible with a diagnostic; no replacement heatmap is fabricated.

Generated desktop/mobile results and dashboard screenshots are under the frontend's `test-results/` directory. Representative screenshots were visually inspected for layout/overflow. Browser emulation is not a physical-phone or complete assistive-technology audit.

Additional integration defects found and fixed during verification:

- Windows npm-generated tool wrappers misparsed the `&` in the existing directory. Scripts now invoke Node tool entrypoints directly without renaming the folder.
- A missing favicon caused the first desktop console-error assertion to fail. Added a local SVG icon and explicit HTML link; the full suite passed after the fix.
- Chart-data print/forced-color styles originally changed only `display`, leaving screen-reader-only clipping in place. Reset the clipping/geometry and added browser regression assertions.

Remaining non-fatal warnings: Vite's minified JavaScript chunk is 675.63 kB (199.13 kB gzip), above its 500 kB advisory; Playwright's terminal color-environment warning; Starlette/httpx TestClient deprecation. No runtime fallback or package upgrade was introduced to hide these warnings.

### Not tested / not claimed

- Genuine known-Real/known-Fake quality evaluation, `real_267.jpg`, validation threshold comparisons and retraining: **blocked by absent data; not performed**.
- Clean-machine installation, physical mobile devices, Safari/Firefox and a complete keyboard/screen-reader audit: **not tested**. Builds/browser runs used the installed local environment and Edge.
- GUI spawning by `Start-DeepTrace.ps1`: **syntax-checked only**; its underlying services were started and exercised directly.
- Production load/security certification and public multi-user deployment: **not tested or supported by this local demo**.
- Integration corrections do not establish improved model accuracy or make Grad-CAM an authenticity proof.

## Files created or modified

Paths below are workspace-relative. This is the implementation inventory, not a Git diff: the workspace has no Git repository. Generated dependencies, caches, build output and test screenshots are excluded from the source inventory.

### Created

- `README.md`, `AUDIT.md`, `.gitignore`, `Start-DeepTrace.ps1` — setup, audit/evidence, local-file exclusions and optional launcher.
- `backend/tools/evaluate.py` — reproducible non-training evaluation/known-image/validation-only threshold CLI.
- `backend/tests/test_evaluation.py`, `backend/tests/serve_isolated.py` — evaluation-tool tests and disposable-history real-model server.
- Frontend `src/utils.ts`, `src/components/common/Dialog.tsx` — shared validation/export helpers and accessible native-dialog wrapper.
- Frontend `tests/api.test.ts`, `tests/browser/workflow.spec.ts`, `playwright.config.ts`, `public/favicon.svg` — unit/browser regressions, browser configuration and local icon.

### Modified backend

- `backend/app/config.py`, `backend/.env`, `backend/.env.example` — localhost/loopback CORS configuration; no secrets published.
- `backend/app/database.py`, `backend/app/schemas.py` — additive threshold migration, connection lifecycle and explicit response contracts/UTC timestamps.
- `backend/app/routes/health.py`, `backend/app/routes/prediction.py` — readiness, upload errors, threadpool inference and request cleanup.
- `backend/app/services/preprocessing.py`, `model_loader.py`, `prediction_service.py`, `gradcam_service.py`, `history_service.py` — preserved effective resize, validated real-model loading/decision, logged Grad-CAM fallback, separate bounded PNG outputs and metadata persistence. The last four filenames are in the same services directory.
- `backend/app/utils/image_utils.py` — decoded codec, size/pixel/animation checks and filename sanitation.
- `backend/tests/test_api.py`, `backend/README.md` — actual-model isolated tests and backend documentation.

### Modified frontend

All paths in this subsection are relative to `deeptrace-ai---deepfake-image-detection-&-forensics/`:

- `package.json`, `package-lock.json`, `vite.config.ts`, `tsconfig.json`, `.env.example`, `README.md`, `index.html` — reproducible npm workflow, strict checking, real-backend configuration and local startup/docs.
- `src/services/api.ts`, `src/types/index.ts`, `src/context/AppContext.tsx` — validated real API contracts, authoritative server decisions, request cancellation, real history/readiness and endpoint handling.
- `src/pages/Dashboard.tsx`, `DetectionPage.tsx`, `HistoryPage.tsx`, `ModelInfoPage.tsx`, `SystemStatusPage.tsx` — actual data, upload/history workflows, accurate model/health information. All five are in `src/pages/`.
- `src/components/layout/MainLayout.tsx`, `Sidebar.tsx`, `Topbar.tsx` — responsive navigation and analysis reset; all in the layout directory.
- `src/components/modals/ApiConfigModal.tsx`, `src/components/common/StatusBadge.tsx` — actual endpoint testing and readiness presentation.
- `src/components/detection/AnalysisResults.tsx`, `GradCamViewer.tsx`, `ProbabilityBar.tsx` — real scores, original/heatmap/overlay, diagnostics and uncertainty text; all in the detection directory.
- `src/components/dashboard/DetectionChart.tsx`, `StatCard.tsx`, `RecentActivity.tsx`, and `src/index.css` — history-derived charts/status, validated labeled colors, responsive styling and chart-data fallback. The three components are in the dashboard directory.

### Preserved

The original model and threshold remain byte-identical. The existing backend application/routing structure and frontend directory/design were retained; no duplicate application was created. No dataset was deleted, no model was retrained, and the user's normal history was not cleared by tests.
