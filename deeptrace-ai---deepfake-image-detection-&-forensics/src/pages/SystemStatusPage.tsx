import { useState } from 'react';
import { Server, RefreshCw, CheckCircle2, AlertCircle, Sliders, ExternalLink } from 'lucide-react';
import { useApp } from '../context/AppContext';

export function SystemStatusPage() {
  const { backendStatus, healthData, connectionError, lastChecked, checkHealth, apiUrl, setIsConfigModalOpen } = useApp();
  const [retrying, setRetrying] = useState(false);
  const [tab, setTab] = useState('health');
  const ready = backendStatus === 'online';
  const metrics = [
    ['Model loaded', healthData ? healthData.model_loaded ? 'Yes' : 'No' : 'Unknown'],
    ['Saved model name', healthData?.model_name ?? 'Not reported'],
    ['TensorFlow version', healthData?.tensorflow_version ?? 'Not reported'],
    ['Real-score threshold', healthData?.threshold ?? 'Not reported'],
  ];
  return <div className="space-y-6 max-w-5xl mx-auto">
    <div className="flex flex-wrap items-start justify-between gap-4"><div><h2 className="text-2xl font-extrabold">System Status & Backend Health</h2><p className="text-sm text-[#94A3B8] mt-1">Live readiness from the configured Python inference service</p></div><div className="flex flex-wrap gap-2"><button className="btn-secondary" onClick={() => setIsConfigModalOpen(true)}><Sliders size={14} />Configure URL</button><button className="btn-primary" disabled={retrying} onClick={async () => { setRetrying(true); try { await checkHealth(); } finally { setRetrying(false); } }}><RefreshCw size={14} className={retrying ? 'animate-spin' : ''} />Retry Connection</button></div></div>
    <section className={`panel sm:p-6 border ${ready ? 'border-[#10B981]/30 bg-gradient-to-br from-[#10B981]/10 to-[#111B2D]' : 'border-[#F59E0B]/30'}`} aria-live="polite"><div className="flex gap-4 items-start"><Server size={30} className={`shrink-0 ${ready ? 'text-[#10B981]' : 'text-[#F59E0B]'}`} /><div className="min-w-0"><p className="text-xs uppercase font-bold flex items-center gap-2">{ready ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}Backend {backendStatus}</p><h3 className="text-xl font-bold mt-2">{ready ? 'Trained model ready for inference' : backendStatus === 'degraded' ? 'Server reachable; model unavailable' : backendStatus === 'checking' ? 'Checking backend readiness' : 'Unable to reach the backend'}</h3><p className="text-xs text-[#94A3B8] mt-2 break-all">Target endpoint: <code className="text-[#21D4FD]">{apiUrl}</code></p><p className="text-[11px] text-[#94A3B8] mt-2">Last probe: {lastChecked?.toLocaleTimeString() ?? 'Not yet completed'} · Automatic health check every 45s</p></div></div>{connectionError && <p className="error-notice mt-4">{connectionError}</p>}</section>
    <div className="flex flex-wrap gap-2 border-b border-[#243247] pb-2">{[['health', 'Health metrics'], ['routes', 'REST API contract'], ['setup', 'Local setup']].map(([value, label]) => <button key={value} onClick={() => setTab(value)} aria-pressed={tab === value} className={`px-4 py-2 rounded-lg text-xs font-semibold ${tab === value ? 'bg-[#152238] text-[#21D4FD]' : 'text-[#94A3B8]'}`}>{label}</button>)}</div>
    {tab === 'health' && <><div className="grid grid-cols-1 sm:grid-cols-2 gap-4">{metrics.map(([label, value]) => <section key={label} className="panel"><h3 className="text-[10px] uppercase tracking-wider text-[#94A3B8] font-semibold">{label}</h3><p className="text-base font-bold font-mono mt-2 break-all">{value}</p></section>)}</div><p className="notice">Device, uptime and global Grad-CAM readiness are not exposed by this health endpoint. Each prediction reports its own visualization availability or diagnostic.</p></>}
    {tab === 'routes' && <section className="panel space-y-4"><div className="flex flex-wrap gap-3 justify-between"><h3 className="text-sm font-bold">FastAPI REST contract</h3><a href={`${apiUrl}/docs`} target="_blank" rel="noreferrer" className="text-xs text-[#21D4FD] inline-flex gap-1 items-center">Open live API docs<ExternalLink size={12} /></a></div>{[
      ['GET', '/api/v1/health', 'Service status, model_loaded, model_name, tensorflow_version, threshold, and optional model_error.'],
      ['POST', '/api/v1/predict', 'Multipart file. Returns record_id, filename, predicted_class, real_probability, fake_probability, confidence_score, threshold, processing_time_ms, nullable PNG Grad-CAM fields and gradcam_error.'],
      ['GET', '/api/v1/history', 'Returns {items, total}. Records use original_filename and created_at; history contains metadata only.'],
      ['GET', '/api/v1/history/{record_id}', 'Fetches the saved metadata for a single record; 404 if absent.'],
      ['DELETE', '/api/v1/history/{record_id}', 'Deletes one record. 204 on success; 404 if absent.'],
      ['DELETE', '/api/v1/history', 'Permanently clears history. 204 on success.'],
    ].map(([method, path, description]) => <div className="p-3 bg-[#080D18] border border-[#243247] rounded-lg" key={`${method}${path}`}><p className="text-xs font-mono break-all"><span className="text-[#21D4FD] mr-2">{method}</span>{path}</p><p className="text-[11px] text-[#94A3B8] mt-2 leading-relaxed">{description}</p></div>)}</section>}
    {tab === 'setup' && <section className="panel space-y-4 text-xs"><h3 className="font-bold text-sm">Use the existing trained-model backend</h3><p className="text-[#94A3B8]">Activate the backend Python environment, install its requirements, and run this command from the backend folder:</p><code className="block p-3 bg-[#080D18] rounded-lg text-[#21D4FD] break-words">python -m uvicorn main:app --host 127.0.0.1 --port 8002</code><p className="text-[#94A3B8]">The backend requires its configured trained model and threshold artifacts. Do not substitute an untrained classifier. Its CORS configuration must include the browser’s exact origin, normally http://127.0.0.1:5173 or http://localhost:5173.</p><p className="notice">Uploaded image content and generated visualizations are not retained. Metadata history belongs to the selected backend, not browser storage. No Gemini API key is required.</p></section>}
  </div>;
}
