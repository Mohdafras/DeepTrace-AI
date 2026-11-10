import { useEffect, useMemo, useRef, useState } from 'react';
import { Search, Trash2, RefreshCw, Download, Eye, ArrowUpDown, Clock } from 'lucide-react';
import { useApp, errorMessage } from '../context/AppContext';
import { apiService } from '../services/api';
import type { DetectionRecord } from '../types';
import { StatusBadge } from '../components/common/StatusBadge';
import { Dialog } from '../components/common/Dialog';
import { clampPage, downloadFile, formatScore, formatTimestamp, historyCsv } from '../utils';

export function HistoryPage() {
  const { history, hasLoadedHistory, isLoadingHistory, historyError, loadHistory, deleteHistoryItem, clearAllHistory, setActiveTab, inspectRecord } = useApp();
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('ALL');
  const [sort, setSort] = useState('date');
  const [descending, setDescending] = useState(true);
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<number | 'all' | null>(null);
  const [detailId, setDetailId] = useState<number | null>(null);
  const [detail, setDetail] = useState<DetectionRecord | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const detailRequest = useRef<AbortController | null>(null);
  useEffect(() => () => detailRequest.current?.abort(), []);

  const filtered = useMemo(() => history.filter(record => (filter === 'ALL' || record.prediction === filter) && `${record.filename} ${record.id}`.toLowerCase().includes(search.trim().toLowerCase())).sort((a, b) => {
    const delta = sort === 'confidence' ? a.confidence - b.confidence : sort === 'time' ? a.processing_time - b.processing_time : new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime() || a.id - b.id;
    return descending ? -delta : delta;
  }), [history, filter, search, sort, descending]);
  const safePage = clampPage(page, filtered.length);
  const pageCount = Math.ceil(filtered.length / 10) || 1;
  const visible = filtered.slice((safePage - 1) * 10, safePage * 10);
  const openDetail = async (id: number) => {
    detailRequest.current?.abort();
    const controller = new AbortController();
    detailRequest.current = controller;
    setDetailId(id); setDetail(null); setDetailError(null);
    try { const data = await apiService.getHistoryRecord(id, controller.signal); if (!controller.signal.aborted) setDetail(data); }
    catch (cause) { if (!controller.signal.aborted) setDetailError(errorMessage(cause)); }
  };
  const openFull = async (id: number) => {
    setPending(true); setError(null);
    try { await inspectRecord(id); }
    catch (cause) { if (!(cause instanceof Error && cause.name === 'AbortError')) setError(errorMessage(cause)); }
    finally { setPending(false); }
  };
  const confirmDelete = async () => {
    if (deleteTarget === null || pending) return;
    setPending(true); setError(null);
    try {
      if (deleteTarget === 'all') await clearAllHistory(); else await deleteHistoryItem(deleteTarget);
      if (deleteTarget === 'all' || deleteTarget === detailId) { setDetailId(null); setDetail(null); }
      setDeleteTarget(null);
    } catch (cause) { setError(errorMessage(cause)); }
    finally { setPending(false); }
  };
  return <div className="space-y-6">
    <div className="flex flex-col sm:flex-row justify-between gap-4"><div><h2 className="text-2xl font-extrabold">Detection History</h2><p className="text-sm text-[#94A3B8] mt-1">Persistent model results from the configured FastAPI server</p></div><div className="flex flex-wrap gap-2 items-start">
      <button className="btn-secondary" onClick={() => void loadHistory()} disabled={isLoadingHistory || pending}><RefreshCw size={14} className={isLoadingHistory ? 'animate-spin' : ''} />Sync</button>
      <button className="btn-secondary" disabled={!filtered.length} onClick={() => downloadFile(historyCsv(filtered), 'DeepTrace_History.csv', 'text/csv;charset=utf-8')}><Download size={14} />Export view CSV</button>
      <button className="btn-danger" disabled={!history.length || pending} onClick={() => { setError(null); setDeleteTarget('all'); }}><Trash2 size={14} />Clear All</button>
    </div></div>
    {historyError && <div role="alert" className="error-notice">{historyError}{hasLoadedHistory && <p className="mt-2">Showing previously loaded records; they may be out of date.</p>}</div>}
    {error && deleteTarget === null && <div role="alert" className="error-notice">{error}</div>}
    <div className="panel flex flex-col lg:flex-row gap-3">
      <div className="relative flex-1"><Search size={15} className="absolute left-3 top-3 text-[#94A3B8]" /><input aria-label="Search history" className="field pl-9" value={search} placeholder="Search filename or record ID…" onChange={event => { setSearch(event.target.value); setPage(1); }} /></div>
      <div className="flex flex-wrap gap-2"><div className="flex gap-1 p-1 bg-[#080D18] border border-[#243247] rounded-lg" aria-label="Filter history class">{['ALL', 'REAL', 'FAKE'].map(value => <button key={value} onClick={() => { setFilter(value); setPage(1); }} aria-pressed={filter === value} className={`text-xs px-3 py-1 rounded ${filter === value ? 'bg-[#152238] text-[#21D4FD]' : 'text-[#94A3B8]'}`}>{value}</button>)}</div><select aria-label="Sort history" className="field w-auto" value={sort} onChange={event => { setSort(event.target.value); setPage(1); }}><option value="date">Sort: Date</option><option value="confidence">Sort: Confidence</option><option value="time">Sort: Latency</option></select><button className="btn-secondary px-3" aria-label={descending ? 'Sort ascending' : 'Sort descending'} onClick={() => { setDescending(!descending); setPage(1); }}><ArrowUpDown size={15} /></button></div>
    </div>
    <section className="bg-[#111B2D] border border-[#243247] rounded-xl overflow-hidden min-w-0" aria-busy={isLoadingHistory}>
      {isLoadingHistory && <p role="status" className="p-4 text-xs text-[#94A3B8]">Refreshing backend history…</p>}
      {!hasLoadedHistory ? <div className="py-12 px-4 text-center text-sm text-[#94A3B8]">{historyError ? 'History unavailable. Use Sync to retry.' : 'Loading detection records…'}</div> : filtered.length === 0 ? <div className="py-12 px-4 text-center"><Clock size={24} className="mx-auto text-[#94A3B8] mb-3" /><h3 className="text-sm font-semibold">{history.length ? 'No Matching Records' : 'No Detection Records Found'}</h3><p className="text-xs text-[#94A3B8] mt-2">{history.length ? 'Adjust your search or class filter.' : 'Run a real image analysis to create a record.'}</p>{!history.length && <button className="btn-primary mt-4" onClick={() => setActiveTab('detection')}>Analyze First Image</button>}</div> : <div className={`overflow-x-auto ${isLoadingHistory ? 'opacity-60' : ''}`} tabIndex={0} role="region" aria-label="Scrollable detection records">
        <table className="w-full text-left text-xs"><caption className="sr-only">Detection metadata. Confidence is a model score, not certainty.</caption><thead className="bg-[#080D18] text-[#94A3B8] text-[10px] uppercase"><tr>{['ID', 'Image filename', 'Prediction', 'Confidence', 'Latency', 'Timestamp', 'Actions'].map(label => <th key={label} scope="col" className="px-4 py-3 whitespace-nowrap">{label}</th>)}</tr></thead><tbody className="divide-y divide-[#243247]">{visible.map(record => <tr key={record.id} className="hover:bg-[#152238]/60"><td className="p-4 font-mono">#{record.id}</td><td className="p-4"><span className="block truncate max-w-[180px]" title={record.filename}>{record.filename}</span></td><td className="p-4 whitespace-nowrap"><StatusBadge prediction={record.prediction} size="sm" /></td><td className="p-4 font-mono tabular-nums">{formatScore(record.confidence)}</td><td className="p-4 font-mono whitespace-nowrap">{record.processing_time.toFixed(3)}s</td><td className="p-4 text-[#94A3B8] whitespace-nowrap">{formatTimestamp(record.timestamp)}</td><td className="p-4"><div className="flex gap-2 whitespace-nowrap"><button className="btn-secondary px-2" disabled={pending} aria-label={`View record ${record.id}`} onClick={() => void openDetail(record.id)}><Eye size={14} /></button><button className="btn-secondary" disabled={pending} onClick={() => void openFull(record.id)}>Full Report</button><button className="btn-danger px-2" disabled={pending} aria-label={`Delete record ${record.id}`} onClick={() => { setError(null); setDeleteTarget(record.id); }}><Trash2 size={14} /></button></div></td></tr>)}</tbody></table>
      </div>}
      {filtered.length > 0 && <div className="p-4 border-t border-[#243247] flex flex-wrap items-center justify-between gap-3 text-xs text-[#94A3B8]"><span>Showing {(safePage - 1) * 10 + 1}–{Math.min(safePage * 10, filtered.length)} of {filtered.length} records</span><div className="flex items-center gap-2"><button className="btn-secondary" disabled={safePage === 1} onClick={() => setPage(safePage - 1)}>Previous</button><span aria-live="polite">{safePage} / {pageCount}</span><button className="btn-secondary" disabled={safePage === pageCount} onClick={() => setPage(safePage + 1)}>Next</button></div></div>}
    </section>
    <p className="text-xs text-[#94A3B8]">History stores metadata only. Original images and Grad-CAM views are not retained. Older records may have no recorded decision threshold.</p>
    {detailId !== null && <Dialog title={`Record #${detailId}`} onClose={() => { detailRequest.current?.abort(); setDetailId(null); }}>
      {detailError ? <p role="alert" className="error-notice">{detailError}</p> : !detail ? <p role="status" className="text-sm">Loading record details…</p> : <div className="space-y-4"><StatusBadge prediction={detail.prediction} /><p className="text-sm break-all font-mono">{detail.filename}</p><dl className="grid grid-cols-2 gap-4 text-xs">{[['Confidence score', formatScore(detail.confidence)], ['Real / fake scores', `${formatScore(detail.real_probability)} / ${formatScore(detail.fake_probability)}`], ['Real-score threshold', detail.threshold ?? 'Not recorded'], ['Inference latency', `${detail.processing_time.toFixed(3)}s`], ['Created at', formatTimestamp(detail.timestamp)]].map(([key, value]) => <div key={key}><dt className="text-[#94A3B8]">{key}</dt><dd className="mt-1">{value}</dd></div>)}</dl><p className="notice">Original and Grad-CAM images are not retained by this metadata-only history.</p><button className="btn-primary" disabled={pending} onClick={() => void openFull(detail.id)}>Open Full Analysis View</button></div>}
    </Dialog>}
    {deleteTarget !== null && <Dialog title={deleteTarget === 'all' ? 'Clear All Detection History?' : `Delete record #${deleteTarget}?`} onClose={() => { if (!pending) setDeleteTarget(null); }}><p className="text-sm text-[#94A3B8]">This permanently deletes {deleteTarget === 'all' ? 'all records' : 'this record'} from the configured backend database. It cannot be undone.</p>{error && <p role="alert" className="error-notice mt-4">{error}</p>}<div className="flex justify-end gap-3 mt-6"><button className="btn-secondary" disabled={pending} onClick={() => setDeleteTarget(null)}>Cancel</button><button className="btn-danger" disabled={pending} onClick={() => void confirmDelete()}>{pending ? 'Deleting…' : deleteTarget === 'all' ? 'Confirm & Delete All' : 'Confirm Delete'}</button></div></Dialog>}
  </div>;
}
