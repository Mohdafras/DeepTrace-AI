import { useEffect, useRef, useState } from 'react';
import { CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';
import { useApp, errorMessage } from '../../context/AppContext';
import { apiService, DEFAULT_API_BASE_URL, normalizeBaseUrl } from '../../services/api';
import { Dialog } from '../common/Dialog';

function ConfigurationForm() {
  const { apiUrl, updateApiUrl, resetApiUrl, backendStatus, connectionError, lastChecked, setIsConfigModalOpen } = useApp();
  const [input, setInput] = useState(apiUrl);
  const [testing, setTesting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);
  const ping = async () => {
    pending.current?.abort();
    const request = new AbortController();
    pending.current = request;
    setError(null); setMessage(null); setTesting(true);
    try {
      const health = await apiService.checkHealth(request.signal, normalizeBaseUrl(input));
      if (!request.signal.aborted) setMessage(health.status === 'online' ? `Draft endpoint verified: model loaded; real-score threshold ${health.threshold}.` : 'Draft endpoint reachable, but the model is not ready.');
    } catch (cause) { if (!request.signal.aborted) setError(errorMessage(cause)); }
    finally { if (!request.signal.aborted) setTesting(false); }
  };
  return <Dialog title="FastAPI Backend Endpoint" onClose={() => setIsConfigModalOpen(false)}>
    <div className="notice mb-5 flex gap-3">
      {backendStatus === 'online' ? <CheckCircle2 size={18} className="shrink-0 text-[#10B981]" /> : <AlertCircle size={18} className="shrink-0 text-[#F59E0B]" />}
      <div><p className="font-semibold">Current endpoint: {backendStatus}</p><p className="font-mono mt-1 break-all">{apiUrl}</p>{lastChecked && <p className="text-[#94A3B8] mt-1">Last checked {lastChecked.toLocaleTimeString()}</p>}{connectionError && <p className="mt-2">{connectionError}</p>}</div>
    </div>
    <form onSubmit={event => {
      event.preventDefault(); pending.current?.abort(); setTesting(false); setError(null);
      try { updateApiUrl(normalizeBaseUrl(input)); setInput(normalizeBaseUrl(input)); setMessage('Endpoint saved. Connection status is shown above; data is being refreshed.'); }
      catch (cause) { setError(errorMessage(cause)); }
    }} className="space-y-4">
      <div><label htmlFor="backend-url" className="block text-xs font-semibold text-[#94A3B8] mb-2">Backend base URL</label>
        <div className="flex flex-col sm:flex-row gap-2"><input id="backend-url" className="field font-mono" type="url" required value={input} placeholder={DEFAULT_API_BASE_URL} onChange={event => { pending.current?.abort(); setTesting(false); setInput(event.target.value); setMessage(null); setError(null); }} /><button type="button" className="btn-secondary" onClick={() => void ping()} disabled={testing}>{testing && <RefreshCw size={14} className="animate-spin" />}Test endpoint</button></div>
        <p className="text-[11px] text-[#94A3B8] mt-2">Testing checks the entered URL without saving it. Changing the endpoint clears the current analysis and reloads history.</p>
      </div>
      {message && <p role="status" className="notice">{message}</p>}{error && <p role="alert" className="error-notice">{error}</p>}
      <div className="p-3 bg-[#080D18] border border-[#243247] rounded-lg text-xs space-y-2"><p className="font-semibold">Start the existing backend from its folder</p><code className="block break-words text-[#21D4FD]">python -m uvicorn main:app --host 127.0.0.1 --port 8002</code><p className="text-[#94A3B8]">CORS must allow the actual frontend origin, including its port (normally http://127.0.0.1:5173). No Gemini key is needed.</p></div>
      <div className="flex flex-wrap gap-2 justify-between border-t border-[#243247] pt-4"><button type="button" className="btn-secondary" onClick={() => { pending.current?.abort(); setTesting(false); setInput(DEFAULT_API_BASE_URL); resetApiUrl(); setMessage('Default endpoint restored.'); setError(null); }}>Reset to default</button><button type="submit" className="btn-primary">Save & Connect</button></div>
    </form>
  </Dialog>;
}
export function ApiConfigModal() {
  const { isConfigModalOpen } = useApp();
  return isConfigModalOpen ? <ConfigurationForm /> : null;
}
