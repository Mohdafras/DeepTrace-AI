import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ApiService, normalizeBaseUrl, normalizeHealth, normalizeHistory, normalizeHistoryRecord, normalizePrediction, normalizeTimestamp, pngDataUrl } from '../src/services/api';
import { clampPage, csvCell, historyCsv, MAX_UPLOAD_BYTES, validateUpload } from '../src/utils';

// Explicit API contract fixtures; these never enter the running application.
const predictionFixture = {
  record_id: 7, filename: 'test-fixture.png', predicted_class: 'REAL',
  real_probability: 0.45, fake_probability: 0.55, confidence_score: 0.45,
  threshold: 0.42, processing_time_ms: 1250,
  gradcam_heatmap: null, gradcam_overlay: null, gradcam_error: 'Test-only unavailable map',
};
const recordFixture = {
  id: 7, original_filename: 'test-fixture.png', predicted_class: 'REAL',
  real_probability: 0.45, fake_probability: 0.55, confidence_score: 0.45,
  threshold: 0.42, processing_time_ms: 1250, created_at: '2026-01-02 03:04:05',
};
const healthyFixture = { status: 'ok', model_loaded: true, model_name: 'test-model', tensorflow_version: 'test-version', threshold: 0.42 };
const png = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=';

test('preserves server REAL label below 0.5 and exact selected-class confidence', () => {
  const result = normalizePrediction(predictionFixture);
  assert.equal(result.prediction, 'REAL');
  assert.equal(result.confidence, 0.45);
  assert.equal(result.threshold, 0.42);
  assert.equal(result.processing_time, 1.25);
  assert.equal(result.timestamp, null); // no fabricated creation time
});
for (const field of ['predicted_class', 'record_id', 'real_probability', 'fake_probability', 'confidence_score', 'processing_time_ms', 'threshold']) {
  test(`rejects missing prediction field ${field} instead of inventing data`, () => {
    const raw: Record<string, unknown> = { ...predictionFixture };
    delete raw[field];
    assert.throws(() => normalizePrediction(raw));
  });
}
test('parses history items and timezone without inventing images', () => {
  const records = normalizeHistory({ items: [recordFixture], total: 1 });
  assert.equal(records[0].filename, recordFixture.original_filename);
  assert.equal(records[0].prediction, 'REAL');
  assert.equal(records[0].timestamp, '2026-01-02T03:04:05.000Z');
  assert.equal(records[0].gradcam_image, null);
  assert.equal(records[0].image_preview, undefined);
  assert.equal(normalizeHistoryRecord({ ...recordFixture, threshold: null }).threshold, null);
});
test('empty history and malformed envelope are distinguished', () => {
  assert.deepEqual(normalizeHistory({ items: [], total: 0 }), []);
  assert.throws(() => normalizeHistory({ records: [], total: 0 }));
  assert.throws(() => normalizeHistory({ items: [], total: 1 }));
});
test('health respects degraded/unloaded status', () => {
  assert.equal(normalizeHealth(healthyFixture).status, 'online');
  assert.equal(normalizeHealth({ ...healthyFixture, status: 'degraded', model_loaded: false }).status, 'degraded');
  assert.equal(normalizeHealth({ ...healthyFixture, threshold: null }).status, 'degraded');
  assert.throws(() => normalizeHealth({ status: 'ok' }));
});
test('rejects invalid probability and date', () => {
  assert.throws(() => normalizePrediction({ ...predictionFixture, real_probability: NaN }));
  assert.throws(() => normalizePrediction({ ...predictionFixture, confidence_score: 1.01 }));
  assert.throws(() => normalizeTimestamp('not a date'));
  assert.equal(normalizeTimestamp('2026-01-02T08:34:05+05:30'), '2026-01-02T03:04:05.000Z');
});
test('separate Grad-CAM payloads and legacy overlay are handled', () => {
  const result = normalizePrediction({ ...predictionFixture, gradcam_image: png, gradcam_heatmap: png });
  assert.equal(result.gradcam_image, `data:image/png;base64,${png}`);
  assert.equal(pngDataUrl(`data:image/png;base64,${png}`), result.gradcam_image);
  assert.equal(pngDataUrl(null), null);
  assert.throws(() => pngDataUrl('https://example.com/image.png'));
  assert.equal(normalizePrediction({ ...predictionFixture, gradcam_image: png }).gradcam_heatmap, null);
});
test('server URLs are normalized and unsafe schemes rejected', () => {
  assert.equal(normalizeBaseUrl(' http://127.0.0.1:8002/ '), 'http://127.0.0.1:8002');
  for (const url of ['javascript:alert(1)', 'https://user:secret@example.com', 'https://example.com?q=1']) {
    assert.throws(() => normalizeBaseUrl(url));
  }
});
for (const extension of ['jpg', 'jpeg', 'png', 'webp']) {
  test(`accepts ${extension} and 10 MiB boundary`, () => {
    assert.equal(validateUpload({ name: `test.${extension}`, type: '', size: MAX_UPLOAD_BYTES }), null);
  });
}
test('rejects empty, oversized, unsupported and mismatched uploads', () => {
  assert.match(validateUpload({ name: 'test.png', type: 'image/png', size: 0 })!, /empty/);
  assert.match(validateUpload({ name: 'test.png', type: 'image/png', size: MAX_UPLOAD_BYTES + 1 })!, /10 MB/);
  assert.match(validateUpload({ name: 'test.gif', type: 'image/gif', size: 10 })!, /JPG/);
  assert.match(validateUpload({ name: 'test.png', type: 'text/plain', size: 10 })!, /file type/);
});
test('CSV quotes filenames and neutralizes spreadsheet formulas', () => {
  assert.equal(csvCell('a,"b".png'), '"a,""b"".png"');
  assert.equal(csvCell('=DANGEROUS()'), '"\'=DANGEROUS()"');
  const csv = historyCsv([normalizeHistoryRecord({ ...recordFixture, original_filename: 'name,#".png' })]);
  assert.ok(csv.includes('"name,#"".png"'));
  assert.ok(csv.includes('"0.42"'));
});
test('pagination clamps when the last page is deleted', () => {
  assert.equal(clampPage(2, 10), 1);
  assert.equal(clampPage(9, 0), 1);
  assert.equal(clampPage(2, 11), 2);
});
test('real upload request uses multipart file field without manual content type', async t => {
  let urlSeen = '';
  t.mock.method(globalThis, 'fetch', async (url: string, options: RequestInit) => {
    urlSeen = String(url);
    assert.equal(options.method, 'POST');
    assert.ok(options.body instanceof FormData);
    assert.ok(options.body.get('file') instanceof File);
    assert.equal(new Headers(options.headers).has('Content-Type'), false);
    return Response.json(predictionFixture);
  });
  const result = await new ApiService('http://127.0.0.1:8003').predictImage(new File(['fixture'], 'test.png', { type: 'image/png' }));
  assert.equal(urlSeen, 'http://127.0.0.1:8003/api/v1/predict');
  assert.equal(result.prediction, 'REAL');
});
test('API errors include validation detail', async t => {
  t.mock.method(globalThis, 'fetch', async () => Response.json({ detail: 'Invalid image' }, { status: 415 }));
  await assert.rejects(new ApiService('http://127.0.0.1:8003').getHistory(), /HTTP 415: Invalid image/);
});
test('offline requests produce actionable errors', async t => {
  t.mock.method(globalThis, 'fetch', async () => { throw new TypeError('Failed to fetch'); });
  await assert.rejects(new ApiService('http://127.0.0.1:8003').checkHealth(), /Cannot reach.*8003/);
});
test('204 deletes need no JSON response', async t => {
  t.mock.method(globalThis, 'fetch', async () => new Response(null, { status: 204 }));
  await new ApiService('http://127.0.0.1:8003').deleteHistoryRecord(7);
  await new ApiService('http://127.0.0.1:8003').clearHistory();
});
test('draft endpoint test does not silently test or save old endpoint', async t => {
  t.mock.method(globalThis, 'fetch', async (url: string) => {
    assert.equal(String(url), 'http://127.0.0.1:8003/api/v1/health');
    return Response.json(healthyFixture);
  });
  const api = new ApiService('http://127.0.0.1:8002');
  await api.checkHealth(undefined, 'http://127.0.0.1:8003');
  assert.equal(api.getBaseUrl(), 'http://127.0.0.1:8002');
});
