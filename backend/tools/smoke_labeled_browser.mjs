// Real browser + real backend + labeled VALIDATION images. No mocked predictions.
// Deletes only records created by this invocation; never clears the user's history.
import { createRequire } from 'node:module';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
const require = createRequire(new URL('../../deeptrace-ai---deepfake-image-detection-&-forensics/package.json', import.meta.url));
const { chromium, expect } = require('@playwright/test');
const [dataset, outputDirectory] = process.argv.slice(2);
if (!dataset || !outputDirectory) throw new Error('Usage: node smoke_labeled_browser.mjs DATASET NEW_OUTPUT_DIRECTORY');
const output = path.resolve(outputDirectory);
if (output.startsWith(path.resolve(dataset) + path.sep)) throw new Error('Output cannot be inside dataset');
await mkdir(output); // Refuse existing directories.
const browser = await chromium.launch({ channel: 'msedge', headless: true });
const results = [];
const api = 'http://127.0.0.1:8002';
try {
  for (const scenario of [{ label: 'Real', width: 1440, height: 1000 }, { label: 'Fake', width: 390, height: 844 }]) {
    const context = await browser.newContext({ viewport: { width: scenario.width, height: scenario.height } });
    const page = await context.newPage();
    page.setDefaultTimeout(60000);
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.addInitScript(url => localStorage.setItem('deeptrace_api_base_url_v2', url), api);
    let recordId;
    const result = { folder_label: scenario.label, viewport: [scenario.width, scenario.height] };
    const navigate = async name => {
      const menu = page.getByRole('button', { name: 'Open navigation' });
      if (await menu.isVisible()) await menu.click();
      await page.getByRole('navigation', { name: 'Main navigation' }).filter({ visible: true }).getByRole('button', { name, exact: true }).click();
    };
    try {
      await page.goto('http://127.0.0.1:5173/');
      await expect(page.getByRole('heading', { name: 'Welcome to DeepTrace AI' })).toBeVisible();
      await navigate('Image Forensics');
      if (scenario.label === 'Real') {
        await page.getByLabel('Choose image for analysis').setInputFiles({ name: 'unsupported.gif', mimeType: 'image/gif', buffer: Buffer.from('GIF89a') });
        await expect(page.getByRole('alert')).toContainText('Choose a JPG');
        await page.getByLabel('Choose image for analysis').setInputFiles({ name: 'corrupt.png', mimeType: 'image/png', buffer: Buffer.from('invalid fixture') });
        await expect(page.getByRole('alert')).toContainText('not a readable image');
      }
      const imagePath = path.join(dataset, 'Validation', scenario.label, `${scenario.label.toLowerCase()}_0.jpg`);
      await page.getByLabel('Choose image for analysis').setInputFiles(imagePath);
      await expect(page.getByRole('img', { name: 'Selected image preview' })).toBeVisible();
      const responsePromise = page.waitForResponse(response => response.url() === api + '/api/v1/predict' && response.request().method() === 'POST', { timeout: 180000 });
      await page.getByRole('button', { name: 'Analyze Image Authenticity', exact: true }).click();
      const response = await responsePromise;
      expect(response.status()).toBe(200);
      const actual = await response.json();
      recordId = actual.record_id;
      await expect(page.getByTestId('prediction-label')).toHaveText(`Model Prediction: ${actual.predicted_class}`);
      for (const [name, score] of [['Real score', actual.real_probability], ['Fake score', actual.fake_probability]]) {
        const meter = page.getByRole('meter', { name, exact: true });
        await expect(meter).toHaveAttribute('aria-valuenow', String(score * 100));
        await expect(meter.locator('..').getByText(score.toFixed(4), { exact: true })).toBeVisible();
      }
      await expect(page.getByText(`Real-score threshold: ${actual.threshold}`, { exact: true })).toBeVisible();
      await expect(page.getByText(`Model confidence score: ${(actual.confidence_score * 100).toFixed(1)}%`, { exact: true })).toBeVisible();
      const maps = ['Original input image'];
      if (!actual.gradcam_error) maps.push('Relative attention heatmap', 'Grad-CAM overlay');
      for (const name of maps) {
        const image = page.getByRole('img', { name, exact: true });
        await expect(image).toBeVisible();
        expect(await image.evaluate(element => element.naturalWidth)).toBeGreaterThan(0);
      }
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
      await page.screenshot({ path: path.join(output, `${scenario.label.toLowerCase()}-${scenario.width}.png`), fullPage: true });
      await navigate('Detection History');
      await page.getByRole('button', { name: `View record ${recordId}`, exact: true }).click();
      await expect(page.getByRole('dialog')).toContainText('Original and Grad-CAM images are not retained');
      await page.getByRole('button', { name: `Close Record #${recordId}` }).click();
      expect(errors).toEqual([]);
      Object.assign(result, { passed: true, predicted_class: actual.predicted_class, p_real: actual.real_probability,
        p_fake: actual.fake_probability, confidence: actual.confidence_score, threshold: actual.threshold,
        processing_time_ms: actual.processing_time_ms, gradcam_error: actual.gradcam_error, history_detail_verified: true });
    } catch (error) {
      result.passed = false;
      result.error = String(error);
      await page.screenshot({ path: path.join(output, `failure-${scenario.label.toLowerCase()}.png`), fullPage: true });
      throw error;
    } finally {
      if (recordId !== undefined) {
        const deletion = await context.request.delete(`${api}/api/v1/history/${recordId}`);
        result.own_history_record_deleted = deletion.status() === 204;
        expect(deletion.status()).toBe(204);
      }
      results.push(result);
      await writeFile(path.join(output, 'results.json'), JSON.stringify({ scope: 'Labeled validation-image integration smoke, NOT accuracy evaluation', results }, null, 2));
      await context.close();
    }
  }
  console.log(JSON.stringify(results, null, 2));
} finally {
  await browser.close();
}
