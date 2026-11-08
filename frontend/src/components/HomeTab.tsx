import React from 'react';
import { Search, X, Clipboard, RefreshCw, AlertTriangle, DownloadCloud, Film, Music, Check, Play } from 'lucide-react';
import { AnalysisData, FormatOption } from '../types';

interface HomeTabProps {
  darkMode: boolean;
  urlInput: string;
  setUrlInput: (val: string) => void;
  recentUrls: string[];
  analyzing: boolean;
  analysisResult: AnalysisData | null;
  analysisError: string | null;
  mediaType: 'video' | 'audio';
  setMediaType: (type: 'video' | 'audio') => void;
  selectedFormatId: string;
  setSelectedFormatId: (id: string) => void;
  selectedSubtitle: string;
  setSelectedSubtitle: (sub: string) => void;
  availableVideoFormats: FormatOption[];
  availableAudioFormats: FormatOption[];
  onAnalyze: (e: React.FormEvent) => void;
  onPasteClipboard: () => void;
  onAddToQueue: () => void;
}

export const HomeTab: React.FC<HomeTabProps> = ({
  darkMode,
  urlInput,
  setUrlInput,
  recentUrls,
  analyzing,
  analysisResult,
  analysisError,
  mediaType,
  setMediaType,
  selectedFormatId,
  setSelectedFormatId,
  selectedSubtitle,
  setSelectedSubtitle,
  availableVideoFormats,
  availableAudioFormats,
  onAnalyze,
  onPasteClipboard,
  onAddToQueue,
}) => {
  return (
    <div className="space-y-6">
      {/* URL Input Bar */}
      <div className={`p-6 rounded-2xl border ${darkMode ? 'bg-zinc-900/40 border-zinc-800' : 'bg-white border-zinc-200 shadow-sm'}`}>
        <h3 className="text-base font-semibold mb-1">Analyze & Download Media</h3>
        <p className="text-xs text-zinc-500 mb-4">
          Enter an authorized video, playlist, or streaming URL to discover available streams and queue downloads.
        </p>

        <form onSubmit={onAnalyze} className="flex gap-2">
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
                onClick={onPasteClipboard}
                className="px-2.5 py-1 rounded-md text-xs font-medium text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 flex items-center gap-1"
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

        {recentUrls.length > 0 && (
          <div className="mt-3 flex items-center gap-2 flex-wrap">
            <span className="text-xs text-zinc-500 font-medium">Recent:</span>
            {recentUrls.map((rUrl, i) => (
              <button
                key={i}
                type="button"
                onClick={() => { setUrlInput(rUrl); }}
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
          <div className="flex gap-6 items-start">
            {analysisResult.thumbnail && (
              <img 
                src={analysisResult.thumbnail} 
                alt="Thumbnail" 
                className="w-56 h-36 object-cover rounded-xl border border-zinc-800 shrink-0 shadow-md"
              />
            )}
            <div className="space-y-2 flex-1">
              <div className="flex items-center gap-2">
                {analysisResult.is_playlist && (
                  <span className="px-2 py-0.5 rounded text-xs font-semibold bg-indigo-500/20 text-indigo-300">
                    Playlist ({analysisResult.playlist_count} items)
                  </span>
                )}
                <h4 className="font-bold text-base leading-snug">{analysisResult.title}</h4>
              </div>

              <p className="text-xs text-zinc-400">
                Creator: <span className="text-zinc-200">{analysisResult.uploader || 'Unknown'}</span> &bull; Extractor: <span className="text-zinc-200">{analysisResult.extractor}</span> &bull; Duration: <span className="text-zinc-200">{analysisResult.duration ? `${Math.floor(analysisResult.duration / 60)}m ${analysisResult.duration % 60}s` : 'Unknown'}</span>
              </p>
              <p className="text-xs text-zinc-500 line-clamp-3 leading-relaxed">
                {analysisResult.description || 'No description provided.'}
              </p>
            </div>
          </div>

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

              {(analysisResult.subtitles?.length > 0 || analysisResult.automatic_captions?.length > 0) && (
                <div className="flex items-center gap-2 text-xs">
                  <label className="text-zinc-400 font-medium">Subtitles:</label>
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
                      <span className="font-semibold text-xs">
                        {fmt.resolution || fmt.format_note || fmt.ext.toUpperCase()}
                      </span>
                      {isSelected && <Check className="w-4 h-4 text-indigo-400" />}
                    </div>
                    <div className="text-[11px] text-zinc-400 space-y-0.5">
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

            <div className="pt-4 flex justify-end">
              <button
                type="button"
                onClick={onAddToQueue}
                className="px-8 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs transition shadow-lg shadow-indigo-600/30 flex items-center gap-2"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Add to Download Queue</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {!analysisResult && !analyzing && (
        <div className={`p-12 text-center rounded-2xl border border-dashed ${darkMode ? 'border-zinc-800/80 text-zinc-600' : 'border-zinc-200 text-zinc-400'}`}>
          <DownloadCloud className="w-10 h-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm font-medium">Ready to download media</p>
          <p className="text-xs text-zinc-500 mt-1">Enter a video or playlist link above to inspect formats, resolutions, and subtitles.</p>
        </div>
      )}
    </div>
  );
};
