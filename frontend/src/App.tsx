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
  Sun,
  Clipboard,
  X,
  Play,
  Film,
  Music,
  Check
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

interface FormatOption {
  format_id: string;
  ext: string;
  resolution?: string;
  width?: number;
  height?: number;
  fps?: number;
  vcodec?: string;
  acodec?: string;
  filesize?: number;
  filesize_approx?: number;
  format_note?: string;
  has_video: boolean;
  has_audio: boolean;
}

interface AnalysisData {
  url: string;
  extractor: string;
  id: string;
  title: string;
  description?: string;
  duration?: number;
  uploader?: string;
  thumbnail?: string;
  formats: FormatOption[];
  subtitles: string[];
  automatic_captions: string[];
  is_playlist?: boolean;
}

interface DownloadTask {
  id: string;
  url: string;
  title: string;
  status: 'pending' | 'downloading' | 'processing' | 'completed' | 'cancelled' | 'failed';
  percent: number;
  downloadedBytes: number;
  totalBytes: number;
  speed: number;
  eta: number;
  filepath?: string;
  error?: string;
}

export function App() {
  const [activeTab, setActiveTab] = useState<ViewMode>('home');
  const [urlInput, setUrlInput] = useState('');
  const [recentUrls, setRecentUrls] = useState<string[]>([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisData | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [darkMode, setDarkMode] = useState(true);

  // Download selection states
  const [mediaType, setMediaType] = useState<'video' | 'audio'>('video');
  const [selectedFormatId, setSelectedFormatId] = useState<string>('');
  const [selectedSubtitle, setSelectedSubtitle] = useState<string>('none');
  const [activeTasks, setActiveTasks] = useState<DownloadTask[]>([]);

  useEffect(() => {
    checkSystemHealth();

    // Listen to real-time streaming progress events from Rust/Python sidecar
    const unlistenPromise = listen('sidecar-event', (event: any) => {
      const payload = event.payload;
      if (payload && payload.data) {
        const jobId = payload.id;
        const progressData = payload.data;

        setActiveTasks((prev) =>
          prev.map((t) => {
            if (t.id === jobId) {
              return {
                ...t,
                status: progressData.status || t.status,
                percent: progressData.percent ?? t.percent,
                downloadedBytes: progressData.downloaded_bytes ?? t.downloadedBytes,
                totalBytes: progressData.total_bytes ?? t.totalBytes,
                speed: progressData.speed ?? t.speed,
                eta: progressData.eta ?? t.eta,
                filepath: progressData.filename ?? t.filepath,
              };
            }
            return t;
          })
        );
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
      setHealth({
        status: 'degraded',
        dependencies: { ffmpeg: false, yt_dlp: true },
      });
    }
  };

  const handlePasteClipboard = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) setUrlInput(text.trim());
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

      // Default format selection
      if (res.formats && res.formats.length > 0) {
        // Pick best video or first format
        setSelectedFormatId(res.formats[0].format_id);
      }

      // Add to recent URLs
      setRecentUrls((prev) => Array.from(new Set([targetUrl, ...prev])).slice(0, 5));
    } catch (err: any) {
      setAnalysisError(err?.toString() || 'Failed to analyze URL');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleStartDownload = async () => {
    if (!analysisResult) return;

    const taskId = 'job-' + Math.random().toString(36).substring(2, 9);
    const newTask: DownloadTask = {
      id: taskId,
      url: analysisResult.url,
      title: analysisResult.title,
      status: 'downloading',
      percent: 0,
      downloadedBytes: 0,
      totalBytes: 0,
      speed: 0,
      eta: 0,
    };

    setActiveTasks((prev) => [newTask, ...prev]);
    setActiveTab('queue');

    try {
      const res = await invoke<any>('start_download', {
        url: analysisResult.url,
        formatId: selectedFormatId || undefined,
        subtitleLang: selectedSubtitle !== 'none' ? selectedSubtitle : undefined,
      });

      setActiveTasks((prev) =>
        prev.map((t) =>
          t.id === taskId
            ? { ...t, status: 'completed', percent: 100, filepath: res.filepath }
            : t
        )
      );
    } catch (err: any) {
      setActiveTasks((prev) =>
        prev.map((t) =>
          t.id === taskId
            ? { ...t, status: 'failed', error: err?.toString() || 'Download error' }
            : t
        )
      );
    }
  };

  const handleCancelTask = async (taskId: string) => {
    try {
      await invoke('cancel_job', { jobId: taskId });
      setActiveTasks((prev) =>
        prev.map((t) => (t.id === taskId ? { ...t, status: 'cancelled' } : t))
      );
    } catch (err) {
      console.error('Cancel task error:', err);
    }
  };

  // Filter video vs audio formats
  const availableVideoFormats = analysisResult?.formats?.filter((f) => f.has_video) || [];
  const availableAudioFormats = analysisResult?.formats?.filter((f) => f.has_audio && !f.has_video) || [];

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
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                activeTab === 'queue'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                  : 'hover:bg-zinc-800/40 text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <div className="flex items-center gap-3">
                <ListOrdered className="w-4 h-4" />
                <span>Download Queue</span>
              </div>
              {activeTasks.length > 0 && (
                <span className="px-2 py-0.5 text-xs rounded-full bg-indigo-500/30 text-indigo-200">
                  {activeTasks.length}
                </span>
              )}
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
              {/* URL Input Bar */}
              <div className={`p-6 rounded-2xl border ${darkMode ? 'bg-zinc-900/40 border-zinc-800' : 'bg-white border-zinc-200 shadow-sm'}`}>
                <h3 className="text-lg font-medium mb-1">Analyze & Download Media</h3>
                <p className="text-sm text-zinc-500 mb-4">
                  Enter an authorized video, audio, or streaming URL to discover formats and download.
                </p>

                <form onSubmit={handleAnalyze} className="flex gap-2">
                  <div className="relative flex-1">
                    <Search className="absolute left-3.5 top-3.5 w-4 h-4 text-zinc-500" />
                    <input
                      type="text"
                      placeholder="https://www.youtube.com/watch?v=..."
                      value={urlInput}
                      onChange={(e) => setUrlInput(e.target.value)}
                      className={`w-full pl-10 pr-24 py-2.5 rounded-xl border text-sm transition outline-none ${
                        darkMode 
                          ? 'bg-zinc-950/80 border-zinc-800 focus:border-indigo-500 text-zinc-100 placeholder-zinc-600' 
                          : 'bg-zinc-50 border-zinc-200 focus:border-indigo-500 text-zinc-900'
                      }`}
                    />
                    <div className="absolute right-2 top-2 flex items-center gap-1">
                      {urlInput && (
                        <button
                          type="button"
                          onClick={() => setUrlInput('')}
                          className="p-1 rounded-md text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800"
                          title="Clear input"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={handlePasteClipboard}
                        className="px-2 py-1 rounded-md text-xs font-medium text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 flex items-center gap-1"
                        title="Paste from clipboard"
                      >
                        <Clipboard className="w-3.5 h-3.5" />
                        Paste
                      </button>
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={analyzing || !urlInput.trim()}
                    className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium transition shadow-md shadow-indigo-600/20 flex items-center gap-2"
                  >
                    {analyzing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                    <span>{analyzing ? 'Analyzing...' : 'Analyze'}</span>
                  </button>
                </form>

                {/* Recent URLs Chips */}
                {recentUrls.length > 0 && (
                  <div className="mt-3 flex items-center gap-2 flex-wrap">
                    <span className="text-xs text-zinc-500 font-medium">Recent:</span>
                    {recentUrls.map((rUrl, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => {
                          setUrlInput(rUrl);
                        }}
                        className="px-2.5 py-1 rounded-lg bg-zinc-800/60 hover:bg-zinc-800 text-xs text-zinc-400 hover:text-zinc-200 max-w-xs truncate transition"
                      >
                        {rUrl}
                      </button>
                    ))}
                  </div>
                )}

                {analysisError && (
                  <div className="mt-4 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 shrink-0" />
                    <span>{analysisError}</span>
                  </div>
                )}
              </div>

              {/* Analysis & Format Selection Workspace */}
              {analysisResult && (
                <div className={`p-6 rounded-2xl border space-y-6 ${darkMode ? 'bg-zinc-900/40 border-zinc-800' : 'bg-white border-zinc-200 shadow-sm'}`}>
                  {/* Media Header Info */}
                  <div className="flex gap-6 items-start">
                    {analysisResult.thumbnail && (
                      <img 
                        src={analysisResult.thumbnail} 
                        alt="Thumbnail" 
                        className="w-56 h-36 object-cover rounded-xl border border-zinc-800 shrink-0 shadow-md"
                      />
                    )}
                    <div className="space-y-2 flex-1">
                      <h4 className="font-bold text-lg leading-snug">{analysisResult.title}</h4>
                      <p className="text-xs text-zinc-400">
                        Channel/Creator: <span className="text-zinc-200">{analysisResult.uploader || 'Unknown'}</span> &bull; Extractor: <span className="text-zinc-200">{analysisResult.extractor}</span> &bull; Duration: <span className="text-zinc-200">{analysisResult.duration ? `${Math.floor(analysisResult.duration / 60)}m ${analysisResult.duration % 60}s` : 'Unknown'}</span>
                      </p>
                      <p className="text-xs text-zinc-500 line-clamp-3 leading-relaxed">
                        {analysisResult.description || 'No description provided.'}
                      </p>
                    </div>
                  </div>

                  {/* Format Selector Tabs */}
                  <div className="border-t border-zinc-800/80 pt-6 space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 p-1 rounded-xl bg-zinc-950/60 border border-zinc-800">
                        <button
                          type="button"
                          onClick={() => setMediaType('video')}
                          className={`px-4 py-1.5 rounded-lg text-xs font-medium flex items-center gap-2 transition ${
                            mediaType === 'video' ? 'bg-indigo-600 text-white shadow-sm' : 'text-zinc-400 hover:text-zinc-200'
                          }`}
                        >
                          <Film className="w-3.5 h-3.5" />
                          <span>Video & Audio</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => setMediaType('audio')}
                          className={`px-4 py-1.5 rounded-lg text-xs font-medium flex items-center gap-2 transition ${
                            mediaType === 'audio' ? 'bg-indigo-600 text-white shadow-sm' : 'text-zinc-400 hover:text-zinc-200'
                          }`}
                        >
                          <Music className="w-3.5 h-3.5" />
                          <span>Audio Only</span>
                        </button>
                      </div>

                      {/* Subtitle Selector */}
                      {(analysisResult.subtitles.length > 0 || analysisResult.automatic_captions.length > 0) && (
                        <div className="flex items-center gap-2 text-xs">
                          <label className="text-zinc-400">Subtitles:</label>
                          <select
                            value={selectedSubtitle}
                            onChange={(e) => setSelectedSubtitle(e.target.value)}
                            className="px-3 py-1.5 rounded-lg bg-zinc-950 border border-zinc-800 text-xs text-zinc-200 outline-none"
                          >
                            <option value="none">None</option>
                            {analysisResult.subtitles.map((s, idx) => (
                              <option key={'sub-' + idx} value={s}>{s} (author)</option>
                            ))}
                            {analysisResult.automatic_captions.map((a, idx) => (
                              <option key={'auto-' + idx} value={a}>{a} (auto)</option>
                            ))}
                          </select>
                        </div>
                      )}
                    </div>

                    {/* Format Options Grid */}
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                      {(mediaType === 'video' ? availableVideoFormats : availableAudioFormats).slice(0, 9).map((fmt) => {
                        const isSelected = selectedFormatId === fmt.format_id;
                        return (
                          <div
                            key={fmt.format_id}
                            onClick={() => setSelectedFormatId(fmt.format_id)}
                            className={`p-3.5 rounded-xl border cursor-pointer transition ${
                              isSelected
                                ? 'border-indigo-500 bg-indigo-500/10'
                                : 'border-zinc-800/80 bg-zinc-950/40 hover:border-zinc-700'
                            }`}
                          >
                            <div className="flex items-center justify-between mb-1.5">
                              <span className="font-semibold text-sm">
                                {fmt.resolution || fmt.format_note || fmt.ext.toUpperCase()}
                              </span>
                              {isSelected && <Check className="w-4 h-4 text-indigo-400" />}
                            </div>
                            <div className="text-xs text-zinc-400 space-y-0.5">
                              <p>Container: <span className="text-zinc-200 uppercase">{fmt.ext}</span></p>
                              {fmt.fps && <p>Frame Rate: <span className="text-zinc-200">{fmt.fps} fps</span></p>}
                              {fmt.filesize ? (
                                <p>Size: <span className="text-zinc-200">{(fmt.filesize / (1024 * 1024)).toFixed(1)} MB</span></p>
                              ) : fmt.filesize_approx ? (
                                <p>Size: <span className="text-zinc-200">~{(fmt.filesize_approx / (1024 * 1024)).toFixed(1)} MB</span></p>
                              ) : null}
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {/* Action Download Button */}
                    <div className="pt-4 flex justify-end">
                      <button
                        type="button"
                        onClick={handleStartDownload}
                        className="px-8 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition shadow-lg shadow-indigo-600/30 flex items-center gap-2"
                      >
                        <Play className="w-4 h-4 fill-current" />
                        <span>Download Selected Media</span>
                      </button>
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
            <div className="space-y-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-base font-semibold">Active Downloads ({activeTasks.length})</h3>
              </div>

              {activeTasks.length === 0 ? (
                <div className={`p-12 text-center rounded-2xl border ${darkMode ? 'bg-zinc-900/30 border-zinc-800' : 'bg-white border-zinc-200'}`}>
                  <ListOrdered className="w-10 h-10 mx-auto mb-3 text-zinc-600" />
                  <h4 className="font-medium text-sm">Download Queue Empty</h4>
                  <p className="text-xs text-zinc-500 mt-1">Active tasks and non-blocking downloads will appear here.</p>
                </div>
              ) : (
                activeTasks.map((task) => (
                  <div
                    key={task.id}
                    className={`p-5 rounded-2xl border space-y-3 ${darkMode ? 'bg-zinc-900/40 border-zinc-800' : 'bg-white border-zinc-200 shadow-sm'}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <h4 className="font-semibold text-sm line-clamp-1">{task.title}</h4>
                        <p className="text-xs text-zinc-400 truncate max-w-lg">{task.url}</p>
                      </div>

                      <div className="flex items-center gap-3">
                        <span className={`px-2.5 py-1 rounded-md text-xs font-medium uppercase ${
                          task.status === 'completed' ? 'bg-emerald-500/20 text-emerald-400' :
                          task.status === 'failed' ? 'bg-rose-500/20 text-rose-400' :
                          task.status === 'cancelled' ? 'bg-zinc-800 text-zinc-400' :
                          'bg-indigo-500/20 text-indigo-400 animate-pulse'
                        }`}>
                          {task.status}
                        </span>

                        {task.status === 'downloading' && (
                          <button
                            type="button"
                            onClick={() => handleCancelTask(task.id)}
                            className="px-3 py-1 rounded-lg border border-rose-500/30 hover:bg-rose-500/10 text-rose-400 text-xs font-medium transition"
                          >
                            Cancel
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full bg-zinc-800/80 rounded-full h-2 overflow-hidden">
                      <div
                        className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${task.percent}%` }}
                      />
                    </div>

                    {/* Progress Stats */}
                    <div className="flex items-center justify-between text-xs text-zinc-400">
                      <span>{task.percent.toFixed(1)}%</span>
                      {task.speed > 0 && <span>{(task.speed / (1024 * 1024)).toFixed(2)} MB/s</span>}
                      {task.eta > 0 && <span>ETA: {task.eta}s</span>}
                      {task.filepath && <span className="text-zinc-500 truncate max-w-xs">{task.filepath}</span>}
                    </div>

                    {task.error && (
                      <p className="text-xs text-rose-400">{task.error}</p>
                    )}
                  </div>
                ))
              )}
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
                  <p>Active Tasks: <span className="text-zinc-200">{activeTasks.length}</span></p>
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
