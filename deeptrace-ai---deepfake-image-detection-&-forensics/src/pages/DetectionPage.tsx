import { useEffect, useRef, useState } from 'react';
import { UploadCloud, X, Scan, RefreshCw, AlertTriangle, Cpu, Layers, Settings } from 'lucide-react';
import { useApp, errorMessage } from '../context/AppContext';
import { apiService } from '../services/api';
import { validateUpload } from '../utils';

export function DetectionPage() {
  const { setCurrentResult, backendStatus, apiUrl, healthData, setIsConfigModalOpen, setActiveTab, loadHistory } = useApp();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [dimensions, setDimensions] = useState<{ width: number; height: number } | null>(null);
  const [dragging, setDragging] = useState(false);
  const [reading, setReading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const request = useRef<AbortController | null>(null);
  const reader = useRef<FileReader | null>(null);
  const selection = useRef(0);
  const busy = reading || analyzing;
  useEffect(() => () => { selection.current++; reader.current?.abort(); request.current?.abort(); }, []);

  const clear = () => {
    selection.current++; reader.current?.abort();
    setSelectedFile(null); setPreview(null); setDimensions(null); setError(null); setReading(false);
    if (fileInput.current) fileInput.current.value = '';
  };
  const selectFile = (file: File) => {
    if (analyzing) return;
    clear();
    const validationError = validateUpload(file);
    if (validationError) { setError(validationError); return; }
    const generation = selection.current;
    const fileReader = new FileReader();
    reader.current = fileReader;
    setReading(true);
    fileReader.onerror = () => { if (selection.current === generation) { setError('Unable to read the selected file.'); setReading(false); } };
    fileReader.onload = () => {
      if (selection.current !== generation) return;
      const dataUrl = String(fileReader.result);
      const image = new Image();
      image.onload = () => {
        if (selection.current !== generation) return;
        setDimensions({ width: image.naturalWidth, height: image.naturalHeight });
        setPreview(dataUrl); setSelectedFile(file); setReading(false);
      };
      image.onerror = () => { if (selection.current === generation) { setError('The selected file is not a readable image.'); setReading(false); } };
      image.src = dataUrl;
    };
    fileReader.readAsDataURL(file);
  };
  const analyze = async () => {
    if (!selectedFile || !preview || busy || backendStatus !== 'online') return;
    const controller = new AbortController();
    request.current = controller;
    setAnalyzing(true); setError(null);
    try {
      const result = await apiService.predictImage(selectedFile, controller.signal);
      if (controller.signal.aborted) return;
      setCurrentResult({ ...result, image_preview: preview, model_name: healthData?.model_name ?? undefined });
      void loadHistory();
      setActiveTab('results');
    } catch (cause) { if (!controller.signal.aborted) setError(errorMessage(cause)); }
    finally { if (!controller.signal.aborted) setAnalyzing(false); }
  };
  return <div className="space-y-6 max-w-5xl mx-auto">
    <div><h2 className="text-2xl font-extrabold tracking-tight">Image Forensics</h2><p className="mt-1 text-sm text-[#94A3B8]">Upload an image for a real model prediction and Grad-CAM decision support.</p></div>
    {backendStatus !== 'online' && <div className="notice flex flex-col sm:flex-row gap-3 justify-between sm:items-center"><div className="flex gap-2"><AlertTriangle size={18} className="shrink-0 text-[#F59E0B]" /><div><p className="font-semibold">{backendStatus === 'checking' ? 'Checking model readiness…' : backendStatus === 'degraded' ? 'Server reachable; model not ready' : 'FastAPI backend unavailable'}</p><p className="mt-1 text-[#94A3B8] break-all">{apiUrl}</p></div></div><button className="btn-secondary shrink-0" onClick={() => setIsConfigModalOpen(true)}><Settings size={14} />Connection settings</button></div>}
    {error && <div role="alert" className="error-notice"><p className="font-bold text-white">Image analysis could not proceed</p><p className="mt-1">{error}</p></div>}
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      <div className="lg:col-span-7 space-y-4 min-w-0">
        <div onDragOver={event => { event.preventDefault(); if (!busy) setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={event => { event.preventDefault(); setDragging(false); if (!busy && event.dataTransfer.files[0]) selectFile(event.dataTransfer.files[0]); }} className={`min-h-[340px] p-5 sm:p-8 rounded-2xl border-2 border-dashed flex flex-col justify-center text-center transition-colors ${dragging ? 'border-[#21D4FD] bg-[#21D4FD]/10' : 'border-[#243247] bg-[#111B2D]/60'}`}>
          <input ref={fileInput} type="file" aria-label="Choose image for analysis" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp" disabled={busy} className="sr-only" onChange={event => { if (event.target.files?.[0]) selectFile(event.target.files[0]); }} />
          {reading ? <p role="status" className="text-sm text-[#94A3B8]">Reading and validating image…</p> : selectedFile && preview ? <div className="w-full space-y-4">
            <div className="relative rounded-xl bg-[#080D18] p-2 border border-[#243247]"><img src={preview} alt="Selected image preview" className="max-h-[300px] w-full object-contain rounded-lg" /><button onClick={clear} disabled={analyzing} aria-label="Remove image" className="absolute right-3 top-3 p-2 bg-[#080D18] border border-[#243247] rounded-lg"><X size={16} /></button></div>
            <p className="text-xs font-mono break-all">{selectedFile.name}</p><p className="text-[11px] font-mono text-[#94A3B8]">{dimensions?.width} × {dimensions?.height} px · {(selectedFile.size / 1024).toFixed(1)} KB</p>
          </div> : <div className="space-y-4 max-w-sm mx-auto">
            <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-[#21D4FD]/20 to-[#8B5CF6]/20 border border-[#21D4FD]/30 flex items-center justify-center text-[#21D4FD]"><UploadCloud size={30} /></div>
            <h3 className="text-base font-bold">Drag & drop forensic image here</h3><p className="text-xs text-[#94A3B8]">or browse local files on your computer</p>
            <button type="button" className="btn-secondary text-[#21D4FD]" onClick={() => fileInput.current?.click()}>Browse Files</button>
            <p className="text-[11px] text-[#94A3B8] border-t border-[#243247] pt-4">JPG, JPEG, PNG, WEBP · Maximum 10 MB</p>
          </div>}
        </div>
        <div className="flex flex-wrap gap-3">{selectedFile && <button onClick={clear} disabled={busy} className="btn-secondary">Clear Image</button>}<button onClick={() => void analyze()} disabled={!selectedFile || busy || backendStatus !== 'online'} className="btn-primary flex-1 py-3">{analyzing ? <RefreshCw size={16} className="animate-spin" /> : <Scan size={16} />}{analyzing ? 'Analyzing image…' : 'Analyze Image Authenticity'}</button></div>
        {analyzing && <div className="panel space-y-3" role="status" aria-live="polite"><p className="text-sm text-[#21D4FD] font-semibold">Waiting for the model response</p><p className="text-xs text-[#94A3B8]">The server is processing your image and attempting Grad-CAM. Progress stages are not reported by the API.</p><button className="btn-secondary" onClick={() => { request.current?.abort(); setAnalyzing(false); setError('Request cancelled locally. The server may still finish and save a record; check history before retrying.'); }}>Cancel waiting</button></div>}
      </div>
      <div className="lg:col-span-5 space-y-4 min-w-0">
        <section className="panel space-y-3"><h3 className="text-xs font-bold uppercase tracking-wider flex items-center gap-2 border-b border-[#243247] pb-3"><Cpu size={16} className="text-[#21D4FD]" />Detection pipeline</h3><ol className="space-y-3 text-xs text-[#94A3B8] list-decimal pl-4"><li><strong className="text-white">Input:</strong> validate and decode the uploaded image as RGB.</li><li><strong className="text-white">Preprocessing:</strong> resize to 224 × 224. Float32 pixels remain in 0–255; rescaling is inside the saved model.</li><li><strong className="text-white">Inference:</strong> load the trained EfficientNetB0 artifact; compare its real score against the configured threshold.</li><li><strong className="text-white">Explainability:</strong> attempt a relative-attention heatmap and overlay for the selected class.</li></ol></section>
        <section className="panel space-y-2"><h3 className="text-xs font-semibold flex items-center gap-2"><Layers size={15} className="text-[#8B5CF6]" />Privacy & interpretation</h3><p className="text-xs text-[#94A3B8] leading-relaxed">Images are sent to the configured backend. The original preview stays in this session; history stores prediction metadata, not image contents. Model scores are not calibrated certainty or proof of authenticity.</p></section>
      </div>
    </div>
  </div>;
}
