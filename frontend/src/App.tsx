import React, { useState, useEffect } from 'react';
import { 
  DownloadCloud, 
  ListOrdered, 
  History, 
  Settings, 
  Activity, 
  Info, 
  RefreshCw,
  Moon,
  Sun,
  CheckCircle2,
  AlertTriangle,
  Sparkles
} from 'lucide-react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';

import { ViewMode, ToastMessage, HealthStatus, AnalysisData, QueueItem } from './types';
import { HomeTab } from './components/HomeTab';
import { QueueTab } from './components/QueueTab';
import { LibraryTab } from './components/LibraryTab';
import { HistoryTab } from './components/HistoryTab';
import { SettingsTab } from './components/SettingsTab';
import { DiagnosticsTab } from './components/DiagnosticsTab';
import { AboutTab } from './components/AboutTab';

export function App() {
  const [activeTab, setActiveTab] = useState<ViewMode>('home');
  const [urlInput, setUrlInput] = useState('');
  const [recentUrls, setRecentUrls] = useState<string[]>([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisData | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [capabilities, setCapabilities] = useState<any>(null);
  const [darkMode, setDarkMode] = useState(true);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  // Search & Filter in History
  const [historySearch, setHistorySearch] = useState('');

  // Settings State with LocalStorage Persistence
  const [settingsForm, setSettingsForm] = useState(() => {
    const saved = localStorage.getItem('mediadock_settings');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        // Fall back to defaults
      }
    }
    return {
      downloadDir: 'C:\\Users\\ASUS\\Desktop\\STUDY\\PROJECTS\\yt_dlp_backend\\downloads',
      maxConcurrent: 3,
      autoConvertAudio: false,
      defaultAudioFormat: 'mp3',
      embedSubtitles: true,
    };
  });

  const handleSaveSettings = () => {
    try {
      localStorage.setItem('mediadock_settings', JSON.stringify(settingsForm));
      addToast('Settings saved successfully', 'success');
    } catch (e) {
      addToast('Failed to save settings', 'error');
    }
  };

  // Download selection states
  const [mediaType, setMediaType] = useState<'video' | 'audio'>('video');
  const [selectedFormatId, setSelectedFormatId] = useState<string>('');
  const [selectedSubtitle, setSelectedSubtitle] = useState<string>('none');
  const [queueItems, setQueueItems] = useState<QueueItem[]>([]);

  const addToast = (text: string, type: 'success' | 'error' | 'info' = 'info') => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, text, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  };

  useEffect(() => {
    checkSystemHealth();
    fetchCapabilities();
    fetchQueueItems();

    // Listen to real-time streaming progress and state change events from Rust/Python sidecar
    const unlistenPromise = listen('sidecar-event', (event: any) => {
      const payload = event.payload;
      if (!payload) return;

      const eventName = payload.event;
      const data = payload.data || {};
      const jobId = data.job_id || payload.id;

      if (eventName === 'progress') {
        setQueueItems((prev) =>
          prev.map((item) => {
            if (item.id === jobId) {
              return {
                ...item,
                percent: data.percent ?? item.percent,
                downloaded_bytes: data.downloaded_bytes ?? item.downloaded_bytes,
                total_bytes: data.total_bytes ?? item.total_bytes,
                speed: data.speed ?? item.speed,
                eta: data.eta ?? item.eta,
                filepath: data.filename ?? item.filepath,
              };
            }
            return item;
          })
        );
      } else if (eventName === 'job_state_changed' || eventName === 'job_completed' || eventName === 'job_failed') {
        fetchQueueItems();
        if (eventName === 'job_completed') {
          addToast(`Download completed: ${data.filepath || 'Media file saved'}`, 'success');
        } else if (eventName === 'job_failed') {
          addToast(`Download failed for job ${data.job_id}`, 'error');
        }
      }
    });

    return () => {
      unlistenPromise.then((unlisten) => unlisten());
    };
  }, []);

  const checkSystemHealth = async () => {
    try {
      const res = await invoke<HealthStatus>('check_health');
      setHealth(res);
    } catch (e: any) {
      console.error('Health check failed:', e);
      setHealth({
        status: 'degraded',
        dependencies: { ffmpeg: false, yt_dlp: true },
      });
    }
  };

  const fetchCapabilities = async () => {
    try {
      const caps = await invoke('get_capabilities');
      setCapabilities(caps);
    } catch (e) {
      console.error('Failed to query capabilities:', e);
    }
  };

  const fetchQueueItems = async () => {
    try {
      const res: any = await invoke('queue_list');
      if (res && res.jobs) {
        setQueueItems(res.jobs);
      }
    } catch (e) {
      console.error('Failed to fetch queue list:', e);
    }
  };

  const handlePasteClipboard = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        setUrlInput(text.trim());
        addToast('Pasted URL from clipboard', 'info');
      }
    } catch (err) {
      console.error('Clipboard paste error:', err);
    }
  };

  const handleAnalyze = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const targetUrl = urlInput.trim();
    if (!targetUrl) return;

    setAnalyzing(true);
    setAnalysisError(null);
    setAnalysisResult(null);

    try {
      const res = await invoke<AnalysisData>('analyze_url', { url: targetUrl });
      setAnalysisResult(res);

      if (res.formats && res.formats.length > 0) {
        setSelectedFormatId(res.formats[0].format_id);
      }

      setRecentUrls((prev) => Array.from(new Set([targetUrl, ...prev])).slice(0, 5));
      addToast(`Discovered: ${res.title}`, 'success');
    } catch (err: any) {
      const msg = err?.toString() || 'Failed to analyze URL';
      setAnalysisError(msg);
      addToast(msg, 'error');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleAddToQueue = async () => {
    if (!analysisResult) return;

    try {
      await invoke('queue_add', {
        url: analysisResult.url,
        title: analysisResult.title,
        formatId: selectedFormatId || undefined,
        subtitleLang: selectedSubtitle !== 'none' ? selectedSubtitle : undefined,
      });

      await fetchQueueItems();
      setActiveTab('queue');
      addToast(`Added "${analysisResult.title}" to download queue`, 'success');
    } catch (err: any) {
      addToast(`Queue error: ${err}`, 'error');
    }
  };

  const handleCancelJob = async (jobId: string) => {
    try {
      await invoke('cancel_job', { jobId });
      await fetchQueueItems();
      addToast(`Cancelled job ${jobId}`, 'info');
    } catch (err) {
      console.error('Cancel job error:', err);
    }
  };

  const handleRetryJob = async (jobId: string) => {
    try {
      await invoke('queue_retry', { jobId });
      await fetchQueueItems();
      addToast(`Retrying job ${jobId}`, 'info');
    } catch (err) {
      console.error('Retry job error:', err);
    }
  };

  const handleRemoveJob = async (jobId: string) => {
    try {
      await invoke('queue_remove', { jobId });
      await fetchQueueItems();
      addToast(`Removed job from queue`, 'info');
    } catch (err) {
      console.error('Remove job error:', err);
    }
  };

  const handleRevealFile = async (filepath: string) => {
    try {
      await invoke('reveal_file', { path: filepath });
    } catch (e: any) {
      addToast(`Cannot open file: ${e}`, 'error');
    }
  };

  // Filter video vs audio formats
  const availableVideoFormats = analysisResult?.formats?.filter((f) => f.has_video) || [];
  const availableAudioFormats = analysisResult?.formats?.filter((f) => f.has_audio && !f.has_video) || [];

  // Filter completed items for History
  const completedJobs = queueItems
    .filter((j) => j.state === 'completed')
    .filter((j) => !historySearch || j.title.toLowerCase().includes(historySearch.toLowerCase()));

  return (
    <div className={`flex h-screen w-screen overflow-hidden ${darkMode ? 'bg-zinc-950 text-zinc-100' : 'bg-zinc-50 text-zinc-900'}`}>
      {/* Toast Notification Container */}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 pointer-events-none">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto px-4 py-3 rounded-xl border shadow-xl flex items-center gap-3 text-xs font-medium backdrop-blur-md transition-all animate-in fade-in slide-in-from-bottom-2 ${
              toast.type === 'success'
                ? 'bg-emerald-950/80 border-emerald-500/30 text-emerald-200'
                : toast.type === 'error'
                ? 'bg-rose-950/80 border-rose-500/30 text-rose-200'
                : 'bg-zinc-900/90 border-zinc-700/60 text-zinc-200'
            }`}
          >
            {toast.type === 'success' && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
            {toast.type === 'error' && <AlertTriangle className="w-4 h-4 text-rose-400" />}
            {toast.type === 'info' && <Sparkles className="w-4 h-4 text-indigo-400" />}
            <span>{toast.text}</span>
          </div>
        ))}
      </div>

      {/* Navigation Sidebar */}
      <aside className={`w-64 border-r flex flex-col justify-between p-4 ${darkMode ? 'border-zinc-800 bg-zinc-900/40' : 'border-zinc-200 bg-white'}`}>
        <div>
          {/* Logo Brand */}
          <div className="flex items-center gap-3 px-3 py-4 mb-4">
            <div className="p-2.5 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 text-white shadow-lg shadow-indigo-600/30">
              <DownloadCloud className="w-5 h-5" />
            </div>
            <div>
              <h1 className="font-bold text-base tracking-tight leading-none">MediaDock</h1>
              <p className="text-[11px] text-zinc-500 font-medium mt-1">Desktop Suite</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-1">
            <button
              onClick={() => setActiveTab('home')}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition ${
                activeTab === 'home'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                  : 'hover:bg-zinc-800/40 text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <DownloadCloud className="w-4 h-4" />
              <span>Downloader</span>
            </button>

            <button
              onClick={() => setActiveTab('queue')}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition ${
                activeTab === 'queue'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                  : 'hover:bg-zinc-800/40 text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <div className="flex items-center gap-3">
                <ListOrdered className="w-4 h-4" />
                <span>Download Queue</span>
              </div>
              {queueItems.length > 0 && (
                <span className="px-2 py-0.5 text-xs rounded-full bg-indigo-500/30 text-indigo-200 font-semibold">
                  {queueItems.length}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('history')}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition ${
                activeTab === 'history'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                  : 'hover:bg-zinc-800/40 text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <div className="flex items-center gap-3">
                <History className="w-4 h-4" />
                <span>History</span>
              </div>
              {completedJobs.length > 0 && (
                <span className="px-2 py-0.5 text-xs rounded-full bg-emerald-500/20 text-emerald-300 font-semibold">
                  {completedJobs.length}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('settings')}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition ${
                activeTab === 'settings'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                  : 'hover:bg-zinc-800/40 text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <Settings className="w-4 h-4" />
              <span>Settings</span>
            </button>

            <button
              onClick={() => setActiveTab('diagnostics')}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition ${
                activeTab === 'diagnostics'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                  : 'hover:bg-zinc-800/40 text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <Activity className="w-4 h-4" />
              <span>Diagnostics</span>
            </button>

            <button
              onClick={() => setActiveTab('about')}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition ${
                activeTab === 'about'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                  : 'hover:bg-zinc-800/40 text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <Info className="w-4 h-4" />
              <span>About</span>
            </button>
          </nav>
        </div>

        {/* Bottom Status bar & Theme toggle */}
        <div className="pt-4 border-t border-zinc-800/60 space-y-3">
          <div className="flex items-center justify-between px-2 text-xs text-zinc-500">
            <span className="flex items-center gap-1.5 font-medium">
              <span className={`w-2 h-2 rounded-full ${health?.status === 'healthy' ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`} />
              Engine: {health?.status || 'connecting'}
            </span>
            <button 
              onClick={() => setDarkMode(!darkMode)}
              className="p-1.5 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition"
              title="Toggle theme"
            >
              {darkMode ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>
      </aside>

      {/* Main Workspace Area */}
      <main className="flex-1 flex flex-col overflow-y-auto">
        {/* Header bar */}
        <header className={`h-16 border-b px-8 flex items-center justify-between shrink-0 ${darkMode ? 'border-zinc-800 bg-zinc-900/20 backdrop-blur-md' : 'border-zinc-200 bg-white'}`}>
          <div className="flex items-center gap-2">
            <h2 className="font-semibold text-base capitalize">{activeTab}</h2>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => { checkSystemHealth(); fetchQueueItems(); addToast('Refreshed engine and queue state', 'info'); }}
              className="px-3 py-1.5 text-xs font-medium rounded-lg border border-zinc-700/60 hover:bg-zinc-800 flex items-center gap-1.5 transition text-zinc-300"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh
            </button>
          </div>
        </header>

        {/* Tab Content */}
        <div className="p-8 max-w-6xl w-full mx-auto space-y-6">
          {activeTab === 'home' && (
            <HomeTab
              darkMode={darkMode}
              urlInput={urlInput}
              setUrlInput={setUrlInput}
              recentUrls={recentUrls}
              analyzing={analyzing}
              analysisResult={analysisResult}
              analysisError={analysisError}
              mediaType={mediaType}
              setMediaType={setMediaType}
              selectedFormatId={selectedFormatId}
              setSelectedFormatId={setSelectedFormatId}
              selectedSubtitle={selectedSubtitle}
              setSelectedSubtitle={setSelectedSubtitle}
              availableVideoFormats={availableVideoFormats}
              availableAudioFormats={availableAudioFormats}
              onAnalyze={handleAnalyze}
              onPasteClipboard={handlePasteClipboard}
              onAddToQueue={handleAddToQueue}
            />
          )}

          {activeTab === 'queue' && (
            <QueueTab
              queueItems={queueItems}
              darkMode={darkMode}
              onRefresh={fetchQueueItems}
              onPause={(id) => invoke('queue_pause', { jobId: id }).then(fetchQueueItems)}
              onResume={(id) => invoke('queue_resume', { jobId: id }).then(fetchQueueItems)}
              onCancel={handleCancelJob}
              onRetry={handleRetryJob}
              onRemove={handleRemoveJob}
              onReveal={handleRevealFile}
            />
          )}

          {activeTab === 'library' && (
            <LibraryTab
              completedJobs={completedJobs}
              darkMode={darkMode}
              onReveal={handleRevealFile}
              onRemove={handleRemoveJob}
            />
          )}

          {activeTab === 'history' && (
            <HistoryTab
              completedJobs={completedJobs}
              darkMode={darkMode}
              search={historySearch}
              onSearchChange={setHistorySearch}
              onReveal={handleRevealFile}
              onRemove={handleRemoveJob}
            />
          )}

          {activeTab === 'settings' && (
            <SettingsTab
              darkMode={darkMode}
              settingsForm={settingsForm}
              onSettingsChange={setSettingsForm}
              onSave={handleSaveSettings}
            />
          )}

          {activeTab === 'diagnostics' && (
            <DiagnosticsTab
              darkMode={darkMode}
              health={health}
              capabilities={capabilities}
              queueItems={queueItems}
              completedJobsCount={completedJobs.length}
            />
          )}

          {activeTab === 'about' && (
            <AboutTab darkMode={darkMode} />
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
