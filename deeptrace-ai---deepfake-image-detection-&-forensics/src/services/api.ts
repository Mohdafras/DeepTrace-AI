import type { DetectionRecord, PredictionLabel, PredictionResult, SystemHealth } from '../types';

export const DEFAULT_API_BASE_URL = import.meta.env?.VITE_API_BASE_URL || 'http://127.0.0.1:8002';
const STORAGE_KEY = 'deeptrace_api_base_url_v2';

export function normalizeBaseUrl(value: string): string {
  const url = new URL(value.trim());
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
    throw new Error('Use an HTTP(S) server URL without credentials, query parameters, or a fragment.');
  }
  return url.toString().replace(/\/+$/, '');
}

function object(value: unknown, name = 'response'): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`Invalid ${name}: expected an object.`);
  return value as Record<string, unknown>;
}
function text(value: unknown, field: string): string {
  if (typeof value !== 'string' || !value.trim()) throw new Error(`Invalid API field: ${field}.`);
  return value;
}
function number(value: unknown, field: string, probability = false): number {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || (probability && value > 1)) {
    throw new Error(`Invalid API field: ${field}.`);
  }
  return value;
}
function id(value: unknown): number {
  const result = number(value, 'record ID');
  if (!Number.isSafeInteger(result) || result < 1) throw new Error('Invalid API record ID.');
  return result;
}
function label(value: unknown): PredictionLabel {
  if (value !== 'REAL' && value !== 'FAKE') throw new Error('Invalid API predicted_class.');
  return value;
}
function threshold(value: unknown): number | null {
  return value == null ? null : number(value, 'threshold', true);
}

/** SQLite CURRENT_TIMESTAMP is UTC even when the server omits the timezone suffix. */
export function normalizeTimestamp(value: unknown): string {
  const stamp = text(value, 'created_at');
  const normalized = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(stamp) ? stamp : `${stamp.replace(' ', 'T')}Z`;
  const date = new Date(normalized);
  if (!Number.isFinite(date.getTime())) throw new Error('Invalid API created_at timestamp.');
  return date.toISOString();
}

/** The API returns PNG data, not arbitrary remote URLs. Never reinterpret a missing overlay as a heatmap. */
export function pngDataUrl(value: unknown): string | null {
  if (value == null || value === '') return null;
  const encoded = text(value, 'Grad-CAM PNG').trim().replace(/^data:image\/png;base64,/, '');
  if (!/^[A-Za-z0-9+/]+={0,2}$/.test(encoded) || !encoded.startsWith('iVBORw0KGgo')) {
    throw new Error('Invalid Grad-CAM PNG payload.');
  }
  return `data:image/png;base64,${encoded}`;
}

export function normalizePrediction(value: unknown): PredictionResult {
  const raw = object(value);
  return {
    id: id(raw.record_id),
    filename: text(raw.filename, 'filename'),
    prediction: label(raw.predicted_class), // The trained real-score threshold belongs to the server.
    real_probability: number(raw.real_probability, 'real_probability', true),
    fake_probability: number(raw.fake_probability, 'fake_probability', true),
    confidence: number(raw.confidence_score, 'confidence_score', true),
    processing_time: number(raw.processing_time_ms, 'processing_time_ms') / 1000,
    threshold: number(raw.threshold, 'threshold', true),
    timestamp: null,
    gradcam_image: pngDataUrl(raw.gradcam_overlay ?? raw.gradcam_image),
    gradcam_heatmap: pngDataUrl(raw.gradcam_heatmap),
    gradcam_error: raw.gradcam_error == null ? null : text(raw.gradcam_error, 'gradcam_error'),
  };
}

export function normalizeHistoryRecord(value: unknown): DetectionRecord {
  const raw = object(value, 'history record');
  return {
    id: id(raw.id),
    filename: text(raw.original_filename, 'original_filename'),
    prediction: label(raw.predicted_class),
    real_probability: number(raw.real_probability, 'real_probability', true),
    fake_probability: number(raw.fake_probability, 'fake_probability', true),
    confidence: number(raw.confidence_score, 'confidence_score', true),
    processing_time: number(raw.processing_time_ms, 'processing_time_ms') / 1000,
    threshold: threshold(raw.threshold),
    timestamp: normalizeTimestamp(raw.created_at),
    // History intentionally stores metadata, not the uploaded photograph or visualizations.
    gradcam_image: null,
    gradcam_heatmap: null,
    gradcam_error: null,
  };
}

export function normalizeHistory(value: unknown): DetectionRecord[] {
  const raw = object(value, 'history response');
  if (!Array.isArray(raw.items)) throw new Error('Invalid history response: items must be an array.');
  const total = number(raw.total, 'total');
  if (!Number.isSafeInteger(total) || total !== raw.items.length) throw new Error('Incomplete history response.');
  return raw.items.map(normalizeHistoryRecord).sort((a, b) => b.id - a.id);
}

export function normalizeHealth(value: unknown): SystemHealth {
  const raw = object(value, 'health response');
  if (typeof raw.model_loaded !== 'boolean' || !['ok', 'degraded'].includes(String(raw.status))) {
    throw new Error('Invalid health response: readiness was not reported.');
  }
  const decisionThreshold = threshold(raw.threshold);
  return {
    status: raw.status === 'ok' && raw.model_loaded && decisionThreshold !== null ? 'online' : 'degraded',
    model_loaded: raw.model_loaded,
    model_name: raw.model_name == null ? null : text(raw.model_name, 'model_name'),
    tensorflow_version: text(raw.tensorflow_version, 'tensorflow_version'),
    threshold: decisionThreshold,
    model_error: raw.model_error == null ? null : text(raw.model_error, 'model_error'),
  };
}

export class ApiService {
  private baseUrl: string;
  constructor(baseUrl?: string) {
    this.baseUrl = normalizeBaseUrl(baseUrl ?? this.storedUrl());
  }
  private storedUrl(): string {
    try {
      const current = localStorage.getItem(STORAGE_KEY);
      if (current) return normalizeBaseUrl(current);
      const legacy = localStorage.getItem('deeptrace_api_base_url');
      // Migrate the obsolete template default; retain deliberate custom endpoints.
      if (legacy && !/^http:\/\/(127\.0\.0\.1|localhost):8000\/?$/.test(legacy)) return normalizeBaseUrl(legacy);
    } catch { /* Storage may be unavailable or contain an invalid value. */ }
    return DEFAULT_API_BASE_URL;
  }
  getBaseUrl(): string { return this.baseUrl; }
  setBaseUrl(url: string): void {
    this.baseUrl = normalizeBaseUrl(url);
    try { localStorage.setItem(STORAGE_KEY, this.baseUrl); } catch { /* Session configuration still works. */ }
  }
  resetBaseUrl(): void { this.setBaseUrl(DEFAULT_API_BASE_URL); }

  private async request(path: string, options: RequestInit = {}, timeoutMs = 15000, baseUrl = this.baseUrl): Promise<unknown> {
    const controller = new AbortController();
    let timedOut = false;
    const abort = () => controller.abort();
    options.signal?.addEventListener('abort', abort, { once: true });
    if (options.signal?.aborted) controller.abort();
    const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs);
    try {
      const response = await fetch(`${baseUrl}${path}`, { ...options, headers: { Accept: 'application/json', ...options.headers }, signal: controller.signal });
      const body = response.status === 204 ? '' : await response.text();
      let data: unknown;
      try { data = body ? JSON.parse(body) : null; } catch { throw new Error(`Backend returned non-JSON content (HTTP ${response.status}).`); }
      if (!response.ok) {
        const detail = data && typeof data === 'object' && 'detail' in data ? data.detail : response.statusText;
        throw new Error(`HTTP ${response.status}: ${typeof detail === 'string' ? detail : JSON.stringify(detail)}`);
      }
      return data;
    } catch (error) {
      if (timedOut) throw new Error(`Request timed out after ${timeoutMs / 1000}s. The server may still finish processing; check history before retrying.`);
      if (controller.signal.aborted) throw new DOMException('Request cancelled', 'AbortError');
      if (error instanceof TypeError) throw new Error(`Cannot reach ${baseUrl}. Check the server, network, and CORS allowed frontend origins.`);
      throw error;
    } finally {
      clearTimeout(timer);
      options.signal?.removeEventListener('abort', abort);
    }
  }
  async checkHealth(signal?: AbortSignal, baseUrl?: string): Promise<SystemHealth> {
    return normalizeHealth(await this.request('/api/v1/health', { signal }, 10000, baseUrl ? normalizeBaseUrl(baseUrl) : this.baseUrl));
  }
  async predictImage(file: File, signal?: AbortSignal): Promise<PredictionResult> {
    const body = new FormData();
    body.append('file', file);
    return normalizePrediction(await this.request('/api/v1/predict', { method: 'POST', body, signal }, 120000));
  }
  async getHistory(signal?: AbortSignal): Promise<DetectionRecord[]> {
    return normalizeHistory(await this.request('/api/v1/history', { signal }));
  }
  async getHistoryRecord(recordId: number, signal?: AbortSignal): Promise<DetectionRecord> {
    return normalizeHistoryRecord(await this.request(`/api/v1/history/${id(recordId)}`, { signal }));
  }
  async deleteHistoryRecord(recordId: number, signal?: AbortSignal): Promise<void> {
    await this.request(`/api/v1/history/${id(recordId)}`, { method: 'DELETE', signal });
  }
  async clearHistory(signal?: AbortSignal): Promise<void> {
    await this.request('/api/v1/history', { method: 'DELETE', signal });
  }
}
export const apiService = new ApiService();
