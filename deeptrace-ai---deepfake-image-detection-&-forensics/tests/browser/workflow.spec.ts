import { test, expect, type Page } from '@playwright/test';

// Hard-coded TEST SERVER ONLY: its history is disposable. Never target demo port 8002.
const TEST_API = 'http://127.0.0.1:8003';
async function start(page: Page) {
  await page.addInitScript(url => localStorage.setItem('deeptrace_api_base_url_v2', url), TEST_API);
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Welcome to DeepTrace AI' })).toBeVisible();
}
async function navigate(page: Page, name: string) {
  const mobile = page.getByRole('button', { name: 'Open navigation' });
  if (await mobile.isVisible()) await mobile.click();
  await page.getByRole('navigation', { name: 'Main navigation' }).filter({ visible: true }).getByRole('button', { name, exact: true }).click();
}
async function neutralPng(page: Page) {
  // Synthetic test input, not labeled Real/Fake data and not an accuracy claim.
  const encoded = await page.evaluate(() => {
    const canvas = document.createElement('canvas');
    canvas.width = 224; canvas.height = 224;
    const context = canvas.getContext('2d')!;
    context.fillStyle = 'rgb(128,128,128)'; context.fillRect(0, 0, 224, 224);
    return canvas.toDataURL('image/png').split(',')[1];
  });
  return Buffer.from(encoded, 'base64');
}
async function assertNoOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBeTruthy();
}
async function uploadAndAnalyze(page: Page) {
  await navigate(page, 'Image Forensics');
  await page.getByLabel('Choose image for analysis').setInputFiles({ name: 'synthetic-neutral.png', mimeType: 'image/png', buffer: await neutralPng(page) });
  await expect(page.getByRole('img', { name: 'Selected image preview' })).toBeVisible();
  const reply = page.waitForResponse(response => response.url() === `${TEST_API}/api/v1/predict` && response.request().method() === 'POST', { timeout: 125000 });
  await page.getByRole('button', { name: 'Analyze Image Authenticity', exact: true }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Waiting for the model response' })).toBeVisible();
  const response = await reply;
  expect(response.status()).toBe(200);
  const actual = await response.json();
  // Synthetic inputs exercise the API/UI contract, not a known authenticity label.
  for (const field of ['real_probability', 'fake_probability', 'confidence_score', 'threshold']) {
    expect(Number.isFinite(actual[field]), field).toBe(true);
    expect(actual[field], field).toBeGreaterThanOrEqual(0);
    expect(actual[field], field).toBeLessThanOrEqual(1);
  }
  const health = await page.request.get(`${TEST_API}/api/v1/health`);
  expect(health.ok()).toBe(true);
  expect(actual.threshold).toBe((await health.json()).threshold);
  expect(actual.real_probability + actual.fake_probability).toBeCloseTo(1, 12);
  const expectedClass = actual.real_probability >= actual.threshold ? 'REAL' : 'FAKE';
  expect(actual.predicted_class).toBe(expectedClass);
  expect(actual.confidence_score).toBe(expectedClass === 'REAL' ? actual.real_probability : actual.fake_probability);
  await expect(page.getByTestId('prediction-label')).toHaveText(`Model Prediction: ${actual.predicted_class}`);
  for (const [label, probability] of [['Real score', actual.real_probability], ['Fake score', actual.fake_probability]] as const) {
    const meter = page.getByRole('meter', { name: label, exact: true });
    await expect(meter).toHaveAttribute('aria-valuenow', String(probability * 100));
    const scoreCard = meter.locator('..');
    await expect(scoreCard.getByText(`${(probability * 100).toFixed(1)}%`, { exact: true })).toBeVisible();
    await expect(scoreCard.getByText(probability.toFixed(4), { exact: true })).toBeVisible();
  }
  const confidence = `${(actual.confidence_score * 100).toFixed(1)}%`;
  await expect(page.getByText('Model confidence', { exact: true }).locator('..').getByText(confidence, { exact: true })).toBeVisible();
  await expect(page.getByText(`Model confidence score: ${confidence}`, { exact: true })).toBeVisible();
  await expect(page.getByText(`Real-score threshold: ${actual.threshold}`, { exact: true })).toBeVisible();
  return actual;
}

test.beforeEach(async ({ request }) => {
  // Fail closed BEFORE any DELETE: a port number does not prove DB isolation.
  const isolation = await request.get(`${TEST_API}/__test__/isolation`);
  expect(isolation.ok(), 'Refusing history deletion: start the disposable-history test runner.').toBe(true);
  expect(await isolation.json()).toEqual({ purpose: 'deeptrace-browser-tests', disposable_history: true });
  const health = await request.get(`${TEST_API}/api/v1/health`);
  expect(health.ok(), 'Start backend/tests/serve_isolated.py on port 8003 first.').toBeTruthy();
  expect((await health.json()).model_loaded).toBe(true);
  expect((await request.delete(`${TEST_API}/api/v1/history`)).status()).toBe(204);
});

test('desktop: actual inference, API result consistency, Grad-CAM, metadata CRUD and reset', async ({ page, request }, testInfo) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  await start(page);
  const actual = await uploadAndAnalyze(page);
  const images = ['Original input image'];
  expect(actual.gradcam_image).toBe(actual.gradcam_overlay);
  if (actual.gradcam_error === null) {
    expect(actual.gradcam_heatmap).toEqual(expect.any(String));
    expect(actual.gradcam_overlay).toEqual(expect.any(String));
    images.push('Relative attention heatmap', 'Grad-CAM overlay');
  } else {
    // Some valid model/input pairs have no positive attention; keep the prediction.
    expect(actual.gradcam_error).toEqual(expect.any(String));
    expect(actual.gradcam_error.length).toBeGreaterThan(0);
    expect(actual.gradcam_heatmap).toBeNull();
    expect(actual.gradcam_overlay).toBeNull();
    await expect(page.getByText(actual.gradcam_error, { exact: true })).toHaveCount(2);
    await expect(page.getByRole('img', { name: 'Relative attention heatmap', exact: true })).toHaveCount(0);
    await expect(page.getByRole('img', { name: 'Grad-CAM overlay', exact: true })).toHaveCount(0);
  }
  for (const name of images) {
    const image = page.getByRole('img', { name, exact: true });
    await expect(image).toBeVisible();
    expect(await image.evaluate(element => (element as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
  }
  await assertNoOverflow(page);
  await page.screenshot({ path: testInfo.outputPath('desktop-results.png'), fullPage: true });
  await page.getByRole('button', { name: 'New Analysis', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Browse Files' })).toBeVisible();
  await expect(page.getByTestId('prediction-label')).toHaveCount(0);
  await navigate(page, 'Detection History');
  await expect(page.getByText('synthetic-neutral.png', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: `View record ${actual.record_id}`, exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('Original and Grad-CAM images are not retained');
  await page.getByRole('button', { name: `Close Record #${actual.record_id}` }).click();
  await page.getByRole('button', { name: `Delete record ${actual.record_id}`, exact: true }).click();
  await page.getByRole('button', { name: 'Confirm Delete', exact: true }).click();
  await expect(page.getByText('No Detection Records Found')).toBeVisible();
  expect((await request.get(`${TEST_API}/api/v1/history`)).ok()).toBeTruthy();
  await uploadAndAnalyze(page);
  await navigate(page, 'Dashboard');
  await expect(page.getByText('Classification Distribution', { exact: true })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('desktop-dashboard.png'), fullPage: true });
  // The chart's initially collapsed data table must become readable without color.
  for (const media of [{ forcedColors: 'active' as const }, { forcedColors: 'none' as const, media: 'print' as const }]) {
    await page.emulateMedia(media);
    const table = page.locator('#chart-data');
    await expect(table).toHaveCSS('position', 'static');
    await expect(table).toHaveCSS('clip', 'auto');
    expect((await table.boundingBox())!.height).toBeGreaterThan(20);
    await expect(table).toContainText('synthetic-neutral.png');
  }
  await page.emulateMedia({ forcedColors: 'none', media: 'screen' });
  await navigate(page, 'Detection History');
  await page.getByRole('button', { name: 'Clear All', exact: true }).click();
  await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(page.getByText('synthetic-neutral.png', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Clear All', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm & Delete All', exact: true }).click();
  await expect(page.getByText('No Detection Records Found')).toBeVisible();
  expect(errors).toEqual([]);
});

test('mobile: navigation, upload validation, real prediction and no page overflow', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await start(page);
  await assertNoOverflow(page);
  await navigate(page, 'Image Forensics');
  const input = page.getByLabel('Choose image for analysis');
  await input.setInputFiles({ name: 'unsupported.gif', mimeType: 'image/gif', buffer: Buffer.from('GIF89a') });
  await expect(page.getByRole('alert')).toContainText('Choose a JPG');
  await input.setInputFiles({ name: 'oversized.png', mimeType: 'image/png', buffer: Buffer.alloc(10 * 1024 * 1024 + 1) });
  await expect(page.getByRole('alert')).toContainText('10 MB');
  await input.setInputFiles({ name: 'corrupted.png', mimeType: 'image/png', buffer: Buffer.from('not an image') });
  await expect(page.getByRole('alert')).toContainText('not a readable image');
  await uploadAndAnalyze(page);
  await assertNoOverflow(page);
  await page.screenshot({ path: testInfo.outputPath('mobile-results.png'), fullPage: true });
  for (const name of ['Detection History', 'About the Model', 'System Status', 'Dashboard']) {
    await navigate(page, name);
    await assertNoOverflow(page);
  }
  await page.screenshot({ path: testInfo.outputPath('mobile-dashboard.png'), fullPage: true });
  expect(errors).toEqual([]);
});

test('New Analysis clears selection on the already-open upload page', async ({ page }) => {
  await start(page);
  await navigate(page, 'Image Forensics');
  await page.getByLabel('Choose image for analysis').setInputFiles({ name: 'reset-me.png', mimeType: 'image/png', buffer: await neutralPng(page) });
  await expect(page.getByRole('img', { name: 'Selected image preview' })).toBeVisible();
  await page.getByRole('button', { name: 'New Analysis', exact: true }).click();
  await expect(page.getByRole('img', { name: 'Selected image preview' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Browse Files' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Analyze Image Authenticity', exact: true })).toBeDisabled();
});

test('browser error states: unavailable backend and prediction failure', async ({ page }) => {
  // Error-only network interception is explicit test scaffolding, not a successful model response.
  await page.route('**/api/v1/health', route => route.abort('connectionrefused'));
  await start(page);
  await expect(page.getByText('FastAPI backend disconnected', { exact: true })).toBeVisible();
  await navigate(page, 'Image Forensics');
  await page.getByLabel('Choose image for analysis').setInputFiles({ name: 'sample.png', mimeType: 'image/png', buffer: await neutralPng(page) });
  await expect(page.getByRole('button', { name: 'Analyze Image Authenticity', exact: true })).toBeDisabled();
  await page.unroute('**/api/v1/health');
  await page.reload();
  await page.route('**/api/v1/predict', route => route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'Test-only prediction error' }) }));
  await navigate(page, 'Image Forensics');
  await page.getByLabel('Choose image for analysis').setInputFiles({ name: 'sample.png', mimeType: 'image/png', buffer: await neutralPng(page) });
  await page.getByRole('button', { name: 'Analyze Image Authenticity', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Test-only prediction error');
  await expect(page.getByTestId('prediction-label')).toHaveCount(0);
});

test('browser fallback: keep actual prediction when Grad-CAM is unavailable', async ({ page }) => {
  await start(page);
  await page.route('**/api/v1/predict', async route => {
    // Obtain an actual saved-model response, then simulate ONLY visualization failure.
    const response = await route.fetch({ timeout: 120000 });
    const actual = await response.json();
    await route.fulfill({ response, json: { ...actual, gradcam_image: null, gradcam_overlay: null, gradcam_heatmap: null, gradcam_error: 'Test-only unavailable attention map' } });
  });
  await uploadAndAnalyze(page);
  await expect(page.getByText('Test-only unavailable attention map')).toHaveCount(2);
  await expect(page.getByRole('img', { name: 'Original input image', exact: true })).toBeVisible();
  await expect(page.getByRole('img', { name: 'Grad-CAM overlay', exact: true })).toHaveCount(0);
});
