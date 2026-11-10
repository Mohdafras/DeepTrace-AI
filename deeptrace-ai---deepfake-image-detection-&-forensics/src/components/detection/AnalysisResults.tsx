import { ShieldCheck, AlertTriangle, ArrowLeft, History, Download, Cpu, Calendar, AlertCircle } from 'lucide-react';
import type { PredictionResult } from '../../types';
import { ProbabilityBar } from './ProbabilityBar';
import { GradCamViewer } from './GradCamViewer';
import { downloadFile, formatScore, formatTimestamp } from '../../utils';

export function AnalysisResults({ result, onAnalyzeAnother, onViewHistory }: { result: PredictionResult; onAnalyzeAnother: () => void; onViewHistory: () => void; }) {
  const real = result.prediction === 'REAL';
  const report = () => downloadFile(JSON.stringify({
    project: 'DeepTrace AI', exported_at: new Date().toISOString(), record_id: result.id,
    filename: result.filename, predicted_class: result.prediction, real_probability: result.real_probability,
    fake_probability: result.fake_probability, confidence_score: result.confidence,
    threshold: result.threshold, processing_time_ms: result.processing_time * 1000,
    created_at: result.timestamp, model_name: result.model_name ?? null,
    gradcam_available: Boolean(result.gradcam_image), gradcam_error: result.gradcam_error,
    disclaimer: 'Scores are not calibrated certainty. This model prediction is decision support, not proof of image authenticity.',
  }, null, 2), `DeepTrace_Report_${result.id}.json`, 'application/json');
  return <div className="space-y-6">
    <div className="flex flex-wrap justify-between items-center gap-3"><button className="btn-secondary" onClick={onAnalyzeAnother}><ArrowLeft size={14} />Back to Upload</button><div className="flex flex-wrap gap-2"><button className="btn-secondary" onClick={onViewHistory}><History size={14} />Detection History</button><button className="btn-primary" onClick={report}><Download size={14} />Download Forensic Report</button></div></div>
    <section className={`p-4 sm:p-6 rounded-2xl border shadow-xl ${real ? 'bg-gradient-to-br from-[#10B981]/15 via-[#111B2D] to-[#080D18] border-[#10B981]/40' : 'bg-gradient-to-br from-[#F43F5E]/15 via-[#111B2D] to-[#080D18] border-[#F43F5E]/40'}`}>
      <div className="flex flex-col xl:flex-row justify-between gap-6">
        <div className="flex items-start gap-3 min-w-0"><div className={`p-3 rounded-xl border shrink-0 ${real ? 'text-[#10B981] border-[#10B981]/30 bg-[#10B981]/10' : 'text-[#F43F5E] border-[#F43F5E]/30 bg-[#F43F5E]/10'}`}>{real ? <ShieldCheck size={28} /> : <AlertTriangle size={28} />}</div><div className="min-w-0"><p className="text-[11px] font-mono text-[#94A3B8] break-all">Record #{result.id} · {result.filename}</p><h2 className="text-2xl sm:text-3xl font-extrabold mt-1" data-testid="prediction-label">Model Prediction: {result.prediction}</h2><p className="text-xs sm:text-sm text-[#94A3B8] mt-2">{real ? 'The model classified this image as real using its configured decision threshold.' : 'The model classified this image as fake using its configured decision threshold.'} This is not a verification of authenticity.</p></div></div>
        <div className="grid grid-cols-2 gap-3 shrink-0"><div className="p-3 bg-[#080D18] rounded-xl border border-[#243247]"><p className="text-[10px] text-[#94A3B8] uppercase">Model confidence</p><p className="text-2xl font-bold mt-1">{formatScore(result.confidence)}</p></div><div className="p-3 bg-[#080D18] rounded-xl border border-[#243247]"><p className="text-[10px] text-[#94A3B8] uppercase">Inference latency</p><p className="text-2xl font-bold mt-1">{result.processing_time.toFixed(3)}<span className="text-xs font-normal ml-1">s</span></p></div></div>
      </div>
      <div className="mt-6 pt-5 border-t border-[#243247]"><ProbabilityBar realProbability={result.real_probability} fakeProbability={result.fake_probability} confidence={result.confidence} threshold={result.threshold} /></div>
    </section>
    <section className="panel sm:p-6"><GradCamViewer key={result.id} originalImage={result.image_preview ?? null} gradcamImage={result.gradcam_image} gradcamHeatmap={result.gradcam_heatmap} filename={result.filename} diagnostic={result.gradcam_error} /></section>
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6"><section className="panel space-y-3"><h3 className="flex items-center gap-2 text-xs uppercase font-semibold border-b border-[#243247] pb-3"><Cpu size={16} className="text-[#21D4FD]" />Model & Classification</h3><dl className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs"><div><dt className="text-[#94A3B8]">Saved model name</dt><dd className="mt-1 break-all">{result.model_name ?? 'Not recorded for this result'}</dd></div><div><dt className="text-[#94A3B8]">Decision threshold on real score</dt><dd className="mt-1 font-mono">{result.threshold ?? 'Not recorded'}</dd></div><div><dt className="text-[#94A3B8]">Input tensor</dt><dd className="mt-1">224 × 224 × 3 RGB</dd></div><div><dt className="text-[#94A3B8]">Classification</dt><dd className="mt-1">Binary · REAL / FAKE</dd></div></dl></section>
      <section className="panel space-y-3"><h3 className="flex items-center gap-2 text-xs uppercase font-semibold border-b border-[#243247] pb-3"><Calendar size={16} className="text-[#8B5CF6]" />Record Details</h3><dl className="space-y-3 text-xs"><div><dt className="text-[#94A3B8]">Database creation time</dt><dd className="mt-1">{formatTimestamp(result.timestamp)}</dd></div><div><dt className="text-[#94A3B8]">Persistence</dt><dd className="mt-1">Metadata saved by the server as record #{result.id}; images are not retained.</dd></div><div><dt className="text-[#94A3B8]">Timing scope</dt><dd className="mt-1">Preprocessing, inference and Grad-CAM; excludes database insertion and network transfer. Older history times may exclude Grad-CAM.</dd></div></dl></section></div>
    <div className="notice flex items-start gap-3"><AlertCircle size={18} className="shrink-0" /><p><strong>Forensics disclaimer:</strong> AI predictions may contain errors. Neither confidence scores nor attention maps are definitive proof of image authenticity. Corroborate important decisions with independent evidence.</p></div>
    <div className="flex flex-wrap gap-3"><button className="btn-primary" onClick={onAnalyzeAnother}><ArrowLeft size={15} />Analyze Another Image</button><button className="btn-secondary" onClick={onViewHistory}>Open History Log</button></div>
  </div>;
}
