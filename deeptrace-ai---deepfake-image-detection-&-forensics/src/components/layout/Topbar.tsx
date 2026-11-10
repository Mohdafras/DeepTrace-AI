import { PlusCircle, Menu, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';
import { useApp } from '../../context/AppContext';

export function Topbar() {
  const { activeTab, setActiveTab, backendStatus, setIsConfigModalOpen, mobileNavOpen, setMobileNavOpen } = useApp();
  const pages = {
    dashboard: ['Forensic Analytics Dashboard', 'Dashboard'],
    detection: ['Image Forensics Workspace', 'Forensics / Upload'],
    results: ['Detection Results & Grad-CAM', 'Forensics / Results'],
    history: ['Detection History & Records', 'History / Logs'],
    model: ['About the Detection Model', 'Model / Documentation'],
    status: ['System Health & FastAPI', 'System / Status'],
  };
  const [title, crumb] = pages[activeTab];
  const ready = backendStatus === 'online';
  return <header className="sticky top-0 z-20 h-16 bg-[#080D18]/95 backdrop-blur-md border-b border-[#243247] px-4 sm:px-6 flex items-center justify-between gap-2 sm:gap-4">
    <div className="flex items-center gap-2 sm:gap-4 min-w-0">
      <button onClick={() => setMobileNavOpen(true)} aria-label="Open navigation" aria-expanded={mobileNavOpen} className="md:hidden p-2 text-[#94A3B8] hover:bg-[#152238] rounded-lg shrink-0"><Menu size={20} /></button>
      <div className="min-w-0"><p className="text-[11px] text-[#94A3B8] truncate">DeepTrace AI / <span className="text-[#21D4FD]">{crumb}</span></p><h1 className="text-sm sm:text-base font-bold truncate">{title}</h1></div>
    </div>
    <div className="flex items-center gap-2 shrink-0">
      <button onClick={() => setIsConfigModalOpen(true)} aria-label={`Backend ${backendStatus}. Connection settings`} className={`hidden sm:flex items-center gap-2 px-3 py-2 border rounded-lg text-[11px] font-mono ${ready ? 'text-[#10B981] bg-[#10B981]/10 border-[#10B981]/30' : 'text-[#F59E0B] bg-[#F59E0B]/10 border-[#F59E0B]/30'}`}>
        {ready ? <CheckCircle2 size={14} /> : backendStatus === 'checking' ? <RefreshCw size={14} className="animate-spin" /> : <AlertCircle size={14} />}<span>API {ready ? 'Ready' : backendStatus}</span>
      </button>
      <button onClick={() => setActiveTab('detection')} className="btn-primary"><PlusCircle size={15} /><span className="hidden sm:inline">New Analysis</span><span className="sm:hidden">New</span></button>
    </div>
  </header>;
}
