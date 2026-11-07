import React, { useState, useEffect } from 'react';
import { 
  DownloadCloud, 
  ListOrdered, 
  History, 
  Settings, 
  Activity, 
  Info, 
  Search, 
  AlertTriangle, 
  RefreshCw,
  HardDrive,
  Cpu,
  Moon,
  Sun
} from 'lucide-react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';

type ViewMode = 'home' | 'queue' | 'history' | 'settings' | 'diagnostics' | 'about';

interface HealthStatus {
  status: string;
  dependencies: {
    ffmpeg: boolean | string;
    yt_dlp: boolean | string;
  };
}

export function App() {
  const [activeTab, setActiveTab] = useState<ViewMode>('home');
  const [urlInput, setUrlInput] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [darkMode, setDarkMode] = useState(true);

  // Poll or check health on mount
  useEffect(() => {
    checkSystemHealth();

    // Listen to streaming progress events from Rust/Python sidecar
    const unlistenPromise = listen('sidecar-event', (event: any) => {
      console.log('[Sidecar Event Received]', event.payload);
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

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!urlInput.trim()) return;

    setAnalyzing(true);
    setAnalysisError(null);
    setAnalysisResult(null);

    try {
      const res = await invoke('analyze_url', { url: urlInput.trim() });
      setAnalysisResult(res);
    } catch (err: any) {
      setAnalysisError(err?.toString() || 'Failed to analyze URL');
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className={`flex h-screen w-screen overflow-hidden ${darkMode ? 'bg-zinc-950 text-zinc-100' : 'bg-zinc-50 text-zinc-900'}`}>
      {/* Navigation Sidebar */}
      <aside className={`w-64 border-r flex flex-col justify-between p-4 ${darkMode ? 'border-zinc-800 bg-zinc-900/50' : 'border-zinc-200 bg-white'}`}>
        <div>
          {/* Logo Brand */}
          <div className="flex items-center gap-3 px-3 py-4 mb-4">
            <div className="p-2 rounded-xl bg-indigo-600 text-white shadow-lg shadow-indigo-600/30">
              <DownloadCloud className="w-6 h-6" />
            </div>
            <div>
              <h1 className="font-bold text-lg tracking-tight">MediaDock</h1>
              <p className="text-xs text-zinc-500 font-medium">Desktop Engine</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-1">
            <button
              onClick={() => setActiveTab('home')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
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
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                activeTab === 'queue'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                  : 'hover:bg-zinc-800/40 text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <ListOrdered className="w-4 h-4" />
              <span>Download Queue</span>
            </button>

            <button
              onClick={() => setActiveTab('history')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                activeTab === 'history'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                  : 'hover:bg-zinc-800/40 text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <History className="w-4 h-4" />
              <span>History</span>
            </button>

            <button
              onClick={() => setActiveTab('settings')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
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
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
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
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
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
            <span className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${health?.status === 'healthy' ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`} />
              Sidecar: {health?.status || 'connecting'}
            </span>
            <button 
              onClick={() => setDarkMode(!darkMode)}
              className="p-1.5 rounded-md hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200"
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
        <header className={`h-16 border-b px-8 flex items-center justify-between shrink-0 ${darkMode ? 'border-zinc-800 bg-zinc-900/20' : 'border-zinc-200 bg-white'}`}>
          <div className="flex items-center gap-2">
            <h2 className="font-semibold text-lg capitalize">{activeTab}</h2>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={checkSystemHealth}
              className="px-3 py-1.5 text-xs font-medium rounded-lg border border-zinc-700/60 hover:bg-zinc-800 flex items-center gap-1.5 transition text-zinc-300"
            >
              <RefreshCw className="w-3 h-3" />
              Refresh Engine
            </button>
          </div>
        </header>

        {/* Tab Content */}
        <div className="p-8 max-w-6xl w-full mx-auto space-y-6">
          {activeTab === 'home' && (
            <div className="space-y-6">
              {/* URL Input Hero */}
              <div className={`p-6 rounded-2xl border ${darkMode ? 'bg-zinc-900/40 border-zinc-800' : 'bg-white border-zinc-200 shadow-sm'}`}>
                <h3 className="text-lg font-medium mb-1">Analyze & Download Media</h3>
                <p className="text-sm text-zinc-500 mb-4">
                  Paste any video, stream, or audio URL from supported platforms.
                </p>

                <form onSubmit={handleAnalyze} className="flex gap-3">
                  <div className="relative flex-1">
                    <Search className="absolute left-3.5 top-3.5 w-4 h-4 text-zinc-500" />
                    <input
                      type="text"
                      placeholder="https://www.youtube.com/watch?v=..."
                      value={urlInput}
                      onChange={(e) => setUrlInput(e.target.value)}
                      className={`w-full pl-10 pr-4 py-2.5 rounded-xl border text-sm transition outline-none ${
                        darkMode 
                          ? 'bg-zinc-950/80 border-zinc-800 focus:border-indigo-500 text-zinc-100 placeholder-zinc-600' 
                          : 'bg-zinc-50 border-zinc-200 focus:border-indigo-500 text-zinc-900'
                      }`}
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={analyzing || !urlInput.trim()}
                    className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium transition shadow-md shadow-indigo-600/20 flex items-center gap-2"
                  >
                    {analyzing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                    <span>{analyzing ? 'Analyzing...' : 'Analyze'}</span>
                  </button>
                </form>

                {analysisError && (
                  <div className="mt-4 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 shrink-0" />
                    <span>{analysisError}</span>
                  </div>
                )}
              </div>

              {/* Analysis Results Card */}
              {analysisResult && (
                <div className={`p-6 rounded-2xl border ${darkMode ? 'bg-zinc-900/40 border-zinc-800' : 'bg-white border-zinc-200'}`}>
                  <div className="flex gap-6">
                    {analysisResult.thumbnail && (
                      <img 
                        src={analysisResult.thumbnail} 
                        alt="Thumbnail" 
                        className="w-48 h-32 object-cover rounded-xl border border-zinc-800 shrink-0"
                      />
                    )}
                    <div className="space-y-2 flex-1">
                      <h4 className="font-semibold text-base leading-snug">{analysisResult.title}</h4>
                      <p className="text-xs text-zinc-400">Extractor: {analysisResult.extractor} &bull; Duration: {analysisResult.duration}s</p>
                      <p className="text-xs text-zinc-500 line-clamp-2">{analysisResult.description || 'No description provided.'}</p>
                      
                      <div className="pt-2 flex flex-wrap gap-2">
                        <span className="px-2.5 py-1 rounded-md text-xs font-medium bg-zinc-800 text-zinc-300">
                          {analysisResult.formats?.length || 0} formats discovered
                        </span>
                        <span className="px-2.5 py-1 rounded-md text-xs font-medium bg-zinc-800 text-zinc-300">
                          {analysisResult.subtitles?.length || 0} subtitle tracks
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Empty state when no analysis */}
              {!analysisResult && !analyzing && (
                <div className={`p-12 text-center rounded-2xl border border-dashed ${darkMode ? 'border-zinc-800/80 text-zinc-600' : 'border-zinc-200 text-zinc-400'}`}>
                  <DownloadCloud className="w-12 h-12 mx-auto mb-3 opacity-40" />
                  <p className="text-sm font-medium">Ready to download media</p>
                  <p className="text-xs text-zinc-500 mt-1">Enter a video link above to inspect formats, resolutions, and subtitles.</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'queue' && (
            <div className={`p-12 text-center rounded-2xl border ${darkMode ? 'bg-zinc-900/30 border-zinc-800' : 'bg-white border-zinc-200'}`}>
              <ListOrdered className="w-10 h-10 mx-auto mb-3 text-zinc-600" />
              <h4 className="font-medium text-sm">Download Queue Empty</h4>
              <p className="text-xs text-zinc-500 mt-1">Active tasks and non-blocking downloads will appear here.</p>
            </div>
          )}

          {activeTab === 'history' && (
            <div className={`p-12 text-center rounded-2xl border ${darkMode ? 'bg-zinc-900/30 border-zinc-800' : 'bg-white border-zinc-200'}`}>
              <History className="w-10 h-10 mx-auto mb-3 text-zinc-600" />
              <h4 className="font-medium text-sm">No Download History Yet</h4>
              <p className="text-xs text-zinc-500 mt-1">Downloaded videos and converted tracks are stored in SQLite.</p>
            </div>
          )}

          {activeTab === 'settings' && (
            <div className={`p-6 rounded-2xl border space-y-4 ${darkMode ? 'bg-zinc-900/30 border-zinc-800' : 'bg-white border-zinc-200'}`}>
              <h3 className="text-base font-medium">Engine & Storage Settings</h3>
              <div className="space-y-3 text-sm">
                <div>
                  <label className="block text-xs font-medium text-zinc-400 mb-1">Default Download Folder</label>
                  <input 
                    type="text" 
                    readOnly 
                    value="C:\\Users\\ASUS\\Desktop\\STUDY\\PROJECTS\\yt_dlp_backend\\downloads"
                    className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 text-xs text-zinc-400"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-zinc-400 mb-1">Max Concurrent Downloads</label>
                  <input 
                    type="number" 
                    defaultValue={3}
                    className="w-32 px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 text-xs text-zinc-200"
                  />
                </div>
              </div>
            </div>
          )}

          {activeTab === 'diagnostics' && (
            <div className="grid grid-cols-2 gap-4">
              <div className={`p-5 rounded-2xl border ${darkMode ? 'bg-zinc-900/40 border-zinc-800' : 'bg-white border-zinc-200'}`}>
                <div className="flex items-center gap-2 mb-3 text-indigo-400">
                  <Cpu className="w-5 h-5" />
                  <h4 className="font-medium text-sm">Python Engine Sidecar</h4>
                </div>
                <div className="space-y-1.5 text-xs text-zinc-400">
                  <p>Communication: <span className="text-emerald-400">Stdio JSON Lines</span></p>
                  <p>Health: <span className="text-emerald-400">{health?.status || 'Checking...'}</span></p>
                  <p>FFmpeg: <span className="text-emerald-400">{String(health?.dependencies?.ffmpeg)}</span></p>
                  <p>yt-dlp: <span className="text-emerald-400">{String(health?.dependencies?.yt_dlp)}</span></p>
                </div>
              </div>

              <div className={`p-5 rounded-2xl border ${darkMode ? 'bg-zinc-900/40 border-zinc-800' : 'bg-white border-zinc-200'}`}>
                <div className="flex items-center gap-2 mb-3 text-indigo-400">
                  <HardDrive className="w-5 h-5" />
                  <h4 className="font-medium text-sm">Persistence & Cache</h4>
                </div>
                <div className="space-y-1.5 text-xs text-zinc-400">
                  <p>Database: <span className="text-zinc-200">SQLite (WAL mode enabled)</span></p>
                  <p>Isolation: <span className="text-emerald-400">Sandboxed Local Process</span></p>
                  <p>Active Tasks: <span className="text-zinc-200">0</span></p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'about' && (
            <div className={`p-6 rounded-2xl border space-y-3 ${darkMode ? 'bg-zinc-900/40 border-zinc-800' : 'bg-white border-zinc-200'}`}>
              <h3 className="text-base font-medium">About MediaDock</h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                MediaDock is an open-source, high-performance desktop media manager combining Tauri 2 + Rust, React, and Python's `yt-dlp` media extraction engine.
              </p>
              <div className="pt-2 text-xs text-zinc-500">
                <p>Version: 0.1.0-alpha</p>
                <p>Platform: Tauri 2 + Rust + React 19 + TypeScript</p>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
