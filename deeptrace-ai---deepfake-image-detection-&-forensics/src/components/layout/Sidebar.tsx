import { LayoutDashboard, ScanLine, History, Cpu, Activity, ChevronLeft, ChevronRight, ShieldAlert, Settings, UserCheck } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { Dialog } from '../common/Dialog';
import { version } from '../../../package.json';

export function Sidebar() {
  const { activeTab, setActiveTab, backendStatus, apiUrl, sidebarCollapsed, setSidebarCollapsed, mobileNavOpen, setMobileNavOpen, setIsConfigModalOpen } = useApp();
  const items = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'detection', label: 'Image Forensics', icon: ScanLine },
    { id: 'history', label: 'Detection History', icon: History },
    { id: 'model', label: 'About the Model', icon: Cpu },
    { id: 'status', label: 'System Status', icon: Activity },
  ] as const;
  const navigation = (collapsed: boolean) => <nav aria-label="Main navigation" className="flex-1 py-4 space-y-1.5 overflow-y-auto">
    {items.map(({ id, label, icon: Icon }) => {
      const selected = activeTab === id || (id === 'detection' && activeTab === 'results');
      return <button key={id} onClick={() => setActiveTab(id)} aria-current={selected ? 'page' : undefined} aria-label={label} title={collapsed ? label : undefined}
        className={`w-full flex items-center gap-3 px-3 py-3 rounded-lg text-xs font-medium transition-colors ${selected ? 'bg-[#152238] text-[#21D4FD] border border-[#21D4FD]/30' : 'text-[#94A3B8] hover:text-white hover:bg-[#152238]'}`}>
        <Icon size={18} className="shrink-0" />{!collapsed && <span>{label}</span>}
      </button>;
    })}
  </nav>;
  const ready = backendStatus === 'online';
  return <>
    <aside className={`fixed inset-y-0 left-0 z-30 hidden md:flex flex-col bg-[#0B1220] border-r border-[#243247] transition-[width] duration-200 ${sidebarCollapsed ? 'w-20' : 'w-64'}`}>
      <div className={`flex h-16 border-b border-[#243247] items-center ${sidebarCollapsed ? 'justify-center' : 'px-4 justify-between'}`}>
        {!sidebarCollapsed && <button onClick={() => setActiveTab('dashboard')} className="flex items-center gap-2.5 text-left">
          <span className="p-2.5 rounded-xl bg-[#21D4FD]/10 border border-[#21D4FD]/30 text-[#21D4FD]"><ShieldAlert size={20} /></span>
          <span className="text-sm font-extrabold tracking-wide">DEEPTRACE <span className="text-[#21D4FD]">AI</span></span>
        </button>}
        <button onClick={() => setSidebarCollapsed(value => !value)} aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'} className="p-2 text-[#94A3B8] hover:bg-[#152238] rounded-lg">
          {sidebarCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>
      <div className="px-3 flex-1 flex flex-col min-h-0">{navigation(sidebarCollapsed)}</div>
      <div className="p-3 border-t border-[#243247] space-y-3">
        <button onClick={() => setIsConfigModalOpen(true)} aria-label="Configure backend connection" className={`w-full flex items-center gap-2 p-2 rounded-lg border text-left ${ready ? 'bg-[#10B981]/5 border-[#10B981]/30' : 'bg-[#F59E0B]/5 border-[#F59E0B]/30'}`}>
          <Settings size={17} className={ready ? 'text-[#10B981] shrink-0' : 'text-[#F59E0B] shrink-0'} />
          {!sidebarCollapsed && <span className="min-w-0"><span className="block text-xs font-semibold">API {backendStatus === 'online' ? 'ready' : backendStatus}</span><span className="block truncate text-[10px] font-mono text-[#94A3B8]">{apiUrl}</span></span>}
        </button>
        {!sidebarCollapsed && <><div className="flex items-center gap-2 p-2 bg-[#111B2D] rounded-lg border border-[#243247]"><UserCheck size={18} className="text-[#8B5CF6]" /><div><p className="text-xs font-semibold">Research Workspace</p><p className="text-[10px] text-[#94A3B8]">Local image forensics</p></div></div><p className="text-[10px] text-[#94A3B8] font-mono">DeepTrace AI · v{version}</p></>}
      </div>
    </aside>
    {mobileNavOpen && <Dialog title="Navigation" onClose={() => setMobileNavOpen(false)} drawer>{navigation(false)}<button onClick={() => { setMobileNavOpen(false); setIsConfigModalOpen(true); }} className="btn-secondary w-full">Connection settings</button></Dialog>}
  </>;
}
