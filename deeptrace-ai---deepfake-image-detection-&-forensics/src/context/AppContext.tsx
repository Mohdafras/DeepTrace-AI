import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { apiService, DEFAULT_API_BASE_URL, normalizeBaseUrl } from '../services/api';
import type { AppTab, BackendStatus, DetectionRecord, PredictionResult, SystemHealth } from '../types';

interface AppContextType {
  activeTab: AppTab;
  analysisGeneration: number;
  setActiveTab: (tab: AppTab) => void;
  apiUrl: string;
  updateApiUrl: (url: string) => void;
  resetApiUrl: () => void;
  backendStatus: BackendStatus;
  healthData: SystemHealth | null;
  connectionError: string | null;
  lastChecked: Date | null;
  checkHealth: () => Promise<boolean>;
  currentResult: PredictionResult | null;
  setCurrentResult: React.Dispatch<React.SetStateAction<PredictionResult | null>>;
  history: DetectionRecord[];
  hasLoadedHistory: boolean;
  isLoadingHistory: boolean;
  historyError: string | null;
  loadHistory: () => Promise<void>;
  inspectRecord: (id: number) => Promise<void>;
  deleteHistoryItem: (id: number) => Promise<void>;
  clearAllHistory: () => Promise<void>;
  sidebarCollapsed: boolean;
  setSidebarCollapsed: React.Dispatch<React.SetStateAction<boolean>>;
  mobileNavOpen: boolean;
  setMobileNavOpen: React.Dispatch<React.SetStateAction<boolean>>;
  isConfigModalOpen: boolean;
  setIsConfigModalOpen: React.Dispatch<React.SetStateAction<boolean>>;
}
const AppContext = createContext<AppContextType | undefined>(undefined);
export const errorMessage = (error: unknown) => error instanceof Error ? error.message : 'An unexpected request error occurred.';

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeTab, setTab] = useState<AppTab>('dashboard');
  const [analysisGeneration, setAnalysisGeneration] = useState(0);
  const [apiUrl, setApiUrl] = useState(apiService.getBaseUrl());
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('checking');
  const [healthData, setHealthData] = useState<SystemHealth | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [currentResult, setCurrentResult] = useState<PredictionResult | null>(null);
  const [history, setHistory] = useState<DetectionRecord[]>([]);
  const [hasLoadedHistory, setHasLoadedHistory] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
  const healthRequest = useRef<AbortController | null>(null);
  const historyRequest = useRef<AbortController | null>(null);
  const detailRequest = useRef<AbortController | null>(null);
  const lastStatus = useRef<BackendStatus>('checking');

  const setActiveTab = useCallback((tab: AppTab) => {
    detailRequest.current?.abort();
    if (tab === 'detection') {
      setCurrentResult(null);
      // Remount even on the same tab; cleanup cancels reads/pending UI requests.
      setAnalysisGeneration(generation => generation + 1);
    }
    setTab(tab);
    setMobileNavOpen(false);
    window.scrollTo({ top: 0, behavior: 'instant' });
  }, []);

  const loadHistory = useCallback(async () => {
    historyRequest.current?.abort();
    const request = new AbortController();
    historyRequest.current = request;
    setIsLoadingHistory(true);
    setHistoryError(null);
    try {
      const data = await apiService.getHistory(request.signal);
      if (request.signal.aborted) return;
      setHistory(data);
      setHasLoadedHistory(true);
    } catch (error) {
      if (!request.signal.aborted) setHistoryError(errorMessage(error));
    } finally {
      if (!request.signal.aborted) setIsLoadingHistory(false);
    }
  }, []);

  const checkHealth = useCallback(async (): Promise<boolean> => {
    healthRequest.current?.abort();
    const request = new AbortController();
    healthRequest.current = request;
    try {
      const data = await apiService.checkHealth(request.signal);
      if (request.signal.aborted) return false;
      const recovered = lastStatus.current === 'offline';
      lastStatus.current = data.status;
      setHealthData(data);
      setBackendStatus(data.status);
      setLastChecked(new Date());
      setConnectionError(data.status === 'degraded' ? data.model_error ?? 'Server reachable, but the trained model or threshold is not ready.' : null);
      if (recovered) void loadHistory();
      return data.status === 'online';
    } catch (error) {
      if (!request.signal.aborted) {
        lastStatus.current = 'offline';
        setBackendStatus('offline');
        setHealthData(null);
        setLastChecked(new Date());
        setConnectionError(errorMessage(error));
      }
      return false;
    }
  }, [loadHistory]);

  const updateApiUrl = (url: string) => {
    const normalized = normalizeBaseUrl(url);
    if (normalized === apiService.getBaseUrl()) { void checkHealth(); void loadHistory(); return; }
    healthRequest.current?.abort();
    historyRequest.current?.abort();
    detailRequest.current?.abort();
    apiService.setBaseUrl(normalized);
    setCurrentResult(null);
    setHistory([]);
    setHasLoadedHistory(false);
    setHistoryError(null);
    setHealthData(null);
    setConnectionError(null);
    setLastChecked(null);
    lastStatus.current = 'checking';
    setBackendStatus('checking');
    setApiUrl(normalized);
  };
  const resetApiUrl = () => updateApiUrl(DEFAULT_API_BASE_URL);

  const inspectRecord = async (id: number) => {
    detailRequest.current?.abort();
    const request = new AbortController();
    detailRequest.current = request;
    const record = await apiService.getHistoryRecord(id, request.signal);
    if (request.signal.aborted) return;
    setCurrentResult(record);
    setTab('results');
    setMobileNavOpen(false);
    window.scrollTo({ top: 0, behavior: 'instant' });
  };
  const deleteHistoryItem = async (id: number) => {
    const endpoint = apiService.getBaseUrl();
    await apiService.deleteHistoryRecord(id);
    if (endpoint !== apiService.getBaseUrl()) return;
    historyRequest.current?.abort();
    setIsLoadingHistory(false);
    setHistory(prev => prev.filter(item => item.id !== id));
    setCurrentResult(prev => prev?.id === id ? null : prev);
    await loadHistory();
  };
  const clearAllHistory = async () => {
    const endpoint = apiService.getBaseUrl();
    await apiService.clearHistory();
    if (endpoint !== apiService.getBaseUrl()) return;
    historyRequest.current?.abort();
    setIsLoadingHistory(false);
    setHistory([]);
    setCurrentResult(null);
    await loadHistory();
  };

  useEffect(() => {
    void checkHealth();
    void loadHistory();
    const interval = setInterval(() => { void checkHealth(); }, 45000);
    return () => {
      clearInterval(interval);
      healthRequest.current?.abort();
      historyRequest.current?.abort();
      detailRequest.current?.abort();
    };
  }, [apiUrl, checkHealth, loadHistory]);

  return <AppContext.Provider value={{ activeTab, analysisGeneration, setActiveTab, apiUrl, updateApiUrl, resetApiUrl, backendStatus, healthData, connectionError, lastChecked, checkHealth, currentResult, setCurrentResult, history, hasLoadedHistory, isLoadingHistory, historyError, loadHistory, inspectRecord, deleteHistoryItem, clearAllHistory, sidebarCollapsed, setSidebarCollapsed, mobileNavOpen, setMobileNavOpen, isConfigModalOpen, setIsConfigModalOpen }}>{children}</AppContext.Provider>;
};
export function useApp() {
  const value = useContext(AppContext);
  if (!value) throw new Error('useApp must be used inside AppProvider.');
  return value;
}
