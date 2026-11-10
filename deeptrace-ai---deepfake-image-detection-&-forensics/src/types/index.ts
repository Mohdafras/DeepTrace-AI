export type PredictionLabel = 'REAL' | 'FAKE';
export type AppTab = 'dashboard' | 'detection' | 'results' | 'history' | 'model' | 'status';
export type BackendStatus = 'online' | 'offline' | 'checking' | 'degraded';

/** Validated UI representation. Probabilities/scores remain exactly as returned by the API. */
export interface PredictionResult {
  id: number;
  filename: string;
  prediction: PredictionLabel;
  real_probability: number;
  fake_probability: number;
  confidence: number;
  processing_time: number; // seconds; API milliseconds converted once
  threshold: number | null;
  timestamp: string | null; // unknown for the immediate prediction response
  gradcam_image: string | null;
  gradcam_heatmap: string | null;
  gradcam_error: string | null;
  model_name?: string;
  image_preview?: string; // transient client-only data URL, never persisted
}

export interface DetectionRecord extends PredictionResult {
  timestamp: string;
}

export interface SystemHealth {
  status: 'online' | 'degraded';
  model_loaded: boolean;
  model_name: string | null;
  tensorflow_version: string;
  threshold: number | null;
  model_error: string | null;
}
