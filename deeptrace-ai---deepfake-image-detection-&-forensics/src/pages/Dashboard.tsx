import { useState } from 'react';
import { Scan, ShieldCheck, ShieldAlert, Server, Activity, ArrowRight, Settings, RefreshCw } from 'lucide-react';
import { useApp, errorMessage } from '../context/AppContext';
import { StatCard } from '../components/dashboard/StatCard';
import { DetectionChart } from '../components/dashboard/DetectionChart';
import { RecentActivity } from '../components/dashboard/RecentActivity';

export function Dashboard() {
  const { history, hasLoadedHistory, isLoadingHistory, historyError, loadHistory, healthData, backendStatus, setActiveTab, inspectRecord, setIsConfigModalOpen } = useApp();
  const [range, setRange] = useState('all');
  const [error, setError] = useState<string | null>(null);
  const [inspecting, setInspecting] = useState(false);
  const cutoff = range === 'all' ? 0 : Date.now() - Number(range) * 86400000;
  const filtered = history.filter(record => new Date(record.timestamp).getTime() >= cutoff);
  const real = filtered.filter(record => record.prediction === 'REAL').length;
  const fake = filtered.length - real;
  const ready = backendStatus === 'online';
  return <div className="space-y-6">
    {backendStatus !== 'online' && <div className="notice flex flex-wrap justify-between gap-3 items-center"><div><p className="font-semibold">{backendStatus === 'checking' ? 'Checking FastAPI connection…' : backendStatus === 'degraded' ? 'FastAPI reachable, model not ready' : 'FastAPI backend disconnected'}</p><p className="text-[#94A3B8] mt-1">A ready trained-model backend is required for new inferences.</p></div><button className="btn-secondary" onClick={() => setIsConfigModalOpen(true)}><Settings size={14} />Configure Endpoint</button></div>}
    <section className="relative p-6 sm:p-8 bg-gradient-to-r from-[#111B2D] via-[#152238] to-[#111B2D] border border-[#243247] rounded-2xl shadow-xl"><div className="max-w-2xl"><div className="inline-flex items-center gap-2 px-3 py-1 bg-[#21D4FD]/10 border border-[#21D4FD]/30 rounded-full text-[#21D4FD] text-xs font-semibold mb-3"><Activity size={12} />EfficientNetB0 Forensics Engine</div><h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">Welcome to DeepTrace AI</h2><p className="mt-2 text-sm text-[#94A3B8] leading-relaxed">Analyze images, review model predictions and explore relative model attention with explainable Grad-CAM visualizations.</p><div className="mt-5 flex flex-wrap gap-3"><button className="btn-primary" onClick={() => setActiveTab('detection')}>Start New Analysis<ArrowRight size={15} /></button><button className="btn-secondary" onClick={() => setActiveTab('model')}>Learn About EfficientNetB0</button></div></div></section>
    <div className="flex flex-wrap gap-3 justify-between items-center"><label className="flex gap-2 items-center text-xs text-[#94A3B8]">History range<select className="field w-auto" value={range} onChange={event => setRange(event.target.value)}><option value="all">All records</option><option value="7">Last 7 days</option><option value="30">Last 30 days</option><option value="90">Last 90 days</option></select></label><button className="btn-secondary" onClick={() => void loadHistory()} disabled={isLoadingHistory}><RefreshCw size={14} className={isLoadingHistory ? 'animate-spin' : ''} />Refresh dashboard</button></div>
    {historyError && <p role="alert" className="error-notice">{historyError} {hasLoadedHistory ? 'Showing previously loaded history.' : 'History counts are unavailable, not zero.'}</p>}
    {error && <p role="alert" className="error-notice">{error}</p>}
    {isLoadingHistory && <p role="status" className="text-xs text-[#94A3B8]">Refreshing detection history…</p>}
    <div className={`space-y-6 ${isLoadingHistory && hasLoadedHistory ? 'opacity-60' : ''}`} aria-busy={isLoadingHistory}>
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 sm:gap-6"><StatCard title="Images Analyzed" value={hasLoadedHistory ? filtered.length : '—'} subtitle={hasLoadedHistory ? 'Recorded in selected range' : 'History not loaded'} icon={Scan} accentColor="cyan" /><StatCard title="Predicted Real" value={hasLoadedHistory ? real : '—'} subtitle={hasLoadedHistory ? 'Model classifications' : 'History not loaded'} icon={ShieldCheck} accentColor="green" /><StatCard title="Predicted Fake" value={hasLoadedHistory ? fake : '—'} subtitle={hasLoadedHistory ? 'Model classifications' : 'History not loaded'} icon={ShieldAlert} accentColor="rose" /><StatCard title="Model Status" value={ready ? 'READY' : backendStatus.toUpperCase()} subtitle={ready ? `Real threshold ${healthData?.threshold}` : backendStatus === 'degraded' ? 'Model not ready' : 'Check connection status'} icon={Server} accentColor={ready ? 'cyan' : 'amber'} /></div>
      {hasLoadedHistory && <><DetectionChart history={filtered} /><RecentActivity history={filtered} disabled={inspecting} onSelectRecord={async record => { setInspecting(true); setError(null); try { await inspectRecord(record.id); } catch (cause) { if (!(cause instanceof Error && cause.name === 'AbortError')) setError(errorMessage(cause)); } finally { setInspecting(false); } }} onViewAll={() => setActiveTab('history')} /></>}
    </div>
  </div>;
}
