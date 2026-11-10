# DeepTrace AI frontend

React, TypeScript and Vite interface for the existing trained-model FastAPI service. The UI does not train a model or use Gemini. It never falls back to synthetic inference results.

## Run locally

Requires Node.js 20.19+ or 22.12+ (Node 24 supported).

1. Start the existing backend on `http://127.0.0.1:8002` using the root project's backend instructions.
2. In this frontend folder run `npm ci`, then `npm run dev`.
3. Open `http://127.0.0.1:5173`. The port is strict; another process occupying it must be stopped or explicitly reconfigured.

The default API origin is `http://127.0.0.1:8002`. Optionally copy `.env.example` to `.env.local` and change `VITE_API_BASE_URL` before starting Vite. The connection-settings dialog also supports a browser-local override; use **Reset to default** to remove the effect of a custom endpoint. CORS must allow the exact frontend origin (localhost and 127.0.0.1 are different origins).

## Verify

- `npm run lint` — strict TypeScript checking.
- `npm test` — adapter, contract, upload-validation and export/pagination tests. Fixtures live only under `tests`.
- `npm run build` — type-check and create the production build.
- `npm run preview` — serve the production build on port 5173 (stop the dev server first).
- `npm run test:browser` — Playwright integration tests. Start the backend's isolated test server on **8003** first; the suite rejects other backend ports and never modifies normal port-8002 history. Playwright starts/stops the frontend dev server itself. It uses installed Microsoft Edge by default; set `PLAYWRIGHT_BROWSER_CHANNEL=chromium` to use an installed Playwright Chromium instead.

Browser tests use a generated neutral image as a protocol/real-model integration sample, not labeled evaluation evidence. They check UI agreement with the server rather than claim that the image establishes detection accuracy. Screenshots and browser traces are local generated test outputs, never published.

## Data and model interpretation

The backend classifies REAL when its **real score** is greater than or equal to the configured threshold. The frontend preserves that label and its confidence score, including when the threshold differs from 0.5. Scores are not calibrated certainty.

History stores filenames, predictions, scores, thresholds and timing, not original images or Grad-CAM views. Original previews are transient client-side data. Separate nullable PNG heatmap/overlay outputs are displayed only when returned; diagnostics explain unavailable maps. Older history records may have an unknown threshold. No measured accuracy or dataset composition is asserted without an evaluation report.

Application version is defined in `package.json`. The legacy `bun.lock` predates the integration; `package-lock.json` is the npm installation lock for this workflow.
