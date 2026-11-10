import { useState } from 'react';
import { Layers, Download, Maximize2, Info } from 'lucide-react';
import { Dialog } from '../common/Dialog';

interface Props { originalImage: string | null; gradcamImage: string | null; gradcamHeatmap?: string | null; filename?: string; diagnostic?: string | null; }
export function GradCamViewer({ originalImage, gradcamImage, gradcamHeatmap, filename = 'analysis', diagnostic }: Props) {
  const [view, setView] = useState('all');
  const [zoom, setZoom] = useState<{ src: string; title: string } | null>(null);
  const panels = [
    { id: 'original', title: 'Original input image', src: originalImage, missing: 'Original image is not retained in history. It is available only for a new analysis in this session.' },
    { id: 'heatmap', title: 'Relative attention heatmap', src: gradcamHeatmap ?? null, missing: diagnostic || 'A separate heatmap was not returned or retained for this record.' },
    { id: 'overlay', title: 'Grad-CAM overlay', src: gradcamImage, missing: diagnostic || 'An overlay was not returned or retained for this record.' },
  ];
  const download = (src: string, suffix: string) => {
    const anchor = document.createElement('a');
    anchor.href = src;
    anchor.download = suffix === 'original' ? filename : `${filename.replace(/\.[^/.]+$/, '')}_${suffix}.png`;
    document.body.appendChild(anchor); anchor.click(); anchor.remove();
  };
  return <div className="space-y-4">
    <div className="flex flex-wrap items-start justify-between gap-4 pb-4 border-b border-[#243247]">
      <div className="flex gap-2"><Layers size={18} className="text-[#8B5CF6] shrink-0" /><div><h3 className="text-sm font-semibold">Forensic Visualizations (Grad-CAM)</h3><p className="text-xs text-[#94A3B8] mt-1">Relative model attention, not a pixel-level manipulation mask</p></div></div>
      <div className="flex flex-wrap gap-1 bg-[#080D18] border border-[#243247] p-1 rounded-lg" aria-label="Visualization view">{[{ id: 'all', title: '3-Panel View' }, ...panels.map(panel => ({ id: panel.id, title: panel.id[0].toUpperCase() + panel.id.slice(1) }))].map(tab => <button key={tab.id} aria-pressed={view === tab.id} onClick={() => setView(tab.id)} className={`px-3 py-2 text-xs rounded-md ${view === tab.id ? 'bg-[#152238] text-[#21D4FD]' : 'text-[#94A3B8]'}`}>{tab.title}</button>)}</div>
    </div>
    <div className={`grid gap-4 ${view === 'all' ? 'grid-cols-1 lg:grid-cols-3' : 'grid-cols-1 max-w-2xl mx-auto'}`}>{panels.filter(panel => view === 'all' || panel.id === view).map(panel => <section key={panel.id} className="bg-[#080D18] border border-[#243247] rounded-xl overflow-hidden min-w-0">
      <div className="p-3 flex items-center justify-between gap-2 border-b border-[#243247]"><h4 className="text-xs font-semibold">{panel.title}</h4>{panel.src && <button onClick={() => setZoom({ src: panel.src!, title: panel.title })} aria-label={`Expand ${panel.title}`} className="p-1.5 text-[#94A3B8] hover:text-[#21D4FD]"><Maximize2 size={15} /></button>}</div>
      <div className="aspect-square flex items-center justify-center p-3">{panel.src ? <img src={panel.src} alt={panel.title} className="w-full h-full object-contain rounded-lg" /> : <div className="text-center text-xs text-[#94A3B8] leading-relaxed"><Info size={24} className="mx-auto mb-3" />{panel.missing}</div>}</div>
      {panel.src && <div className="border-t border-[#243247] p-2 flex justify-end"><button onClick={() => download(panel.src!, panel.id)} className="btn-secondary"><Download size={13} />Download {panel.id}</button></div>}
    </section>)}</div>
    {(gradcamHeatmap || gradcamImage) && <div className="flex flex-col sm:flex-row gap-3 sm:items-center text-[11px] text-[#94A3B8]"><div className="h-3 w-36 rounded shrink-0" style={{ background: 'linear-gradient(to right, #eff6ff, #1e40af)' }} role="img" aria-label="Pale blue is lower attention; dark blue is higher attention" /><span>Lower → higher relative model attention</span></div>}
    <p className="text-[11px] text-[#94A3B8]">Generated views preserve aspect ratio and are capped at a 1024px longest edge. High attention does not establish that a region is fake. Visualizations are not stored in history.</p>
    {zoom && <Dialog title={zoom.title} onClose={() => setZoom(null)} wide><img src={zoom.src} alt={zoom.title} className="max-h-[70dvh] w-full object-contain rounded-lg bg-[#080D18]" /></Dialog>}
  </div>;
}
