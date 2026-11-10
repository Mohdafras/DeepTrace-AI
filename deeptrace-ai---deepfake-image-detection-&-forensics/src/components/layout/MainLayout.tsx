import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { ApiConfigModal } from '../modals/ApiConfigModal';
import { AnalysisResults } from '../detection/AnalysisResults';
import { useApp } from '../../context/AppContext';
import { Dashboard } from '../../pages/Dashboard';
import { DetectionPage } from '../../pages/DetectionPage';
import { HistoryPage } from '../../pages/HistoryPage';
import { ModelInfoPage } from '../../pages/ModelInfoPage';
import { SystemStatusPage } from '../../pages/SystemStatusPage';
import { version } from '../../../package.json';

export function MainLayout() {
  const { activeTab, analysisGeneration, setActiveTab, currentResult, apiUrl, sidebarCollapsed } = useApp();
  const renderPage = () => {
    switch (activeTab) {
      case 'dashboard': return <Dashboard />;
      case 'detection': return <DetectionPage key={`${apiUrl}:${analysisGeneration}`} />;
      case 'results': return currentResult
        ? <AnalysisResults result={currentResult} onAnalyzeAnother={() => setActiveTab('detection')} onViewHistory={() => setActiveTab('history')} />
        : <section className="panel text-center"><h2 className="text-lg font-bold">No analysis selected</h2><p className="text-sm text-[#94A3B8] my-4">Upload an image or open a saved history record.</p><button className="btn-primary" onClick={() => setActiveTab('detection')}>Start New Analysis</button></section>;
      case 'history': return <HistoryPage key={apiUrl} />;
      case 'model': return <ModelInfoPage />;
      case 'status': return <SystemStatusPage />;
    }
  };
  return <div className="min-h-screen bg-[#080D18] text-[#F8FAFC] font-sans">
    <a className="skip-link" href="#main-content">Skip to content</a>
    <Sidebar />
    <div className={`min-h-screen flex flex-col min-w-0 transition-[margin] duration-200 ${sidebarCollapsed ? 'md:ml-20' : 'md:ml-64'}`}>
      <Topbar />
      <main id="main-content" tabIndex={-1} className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full min-w-0 mx-auto">{renderPage()}</main>
      <footer className="mt-auto border-t border-[#243247] py-6 px-4 sm:px-8 bg-[#0B1220]/40 text-xs text-[#94A3B8]">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row justify-between gap-3">
          <div><p className="font-semibold text-[#F8FAFC]">DeepTrace AI · Deepfake Image Detection</p><p className="text-[11px] mt-1">EfficientNetB0 with Grad-CAM decision support</p></div>
          <p className="text-[11px]">FastAPI · TensorFlow / Keras · v{version}</p>
        </div>
      </footer>
    </div>
    <ApiConfigModal />
  </div>;
}
