import React from 'react';
import { RefreshCw, ListOrdered, Play, RotateCcw, Trash2, FolderOpen } from 'lucide-react';
import type { QueueItem } from '../types';

interface QueueTabProps {
  queueItems: QueueItem[];
  darkMode: boolean;
  onRefresh: () => void;
  onPause: (id: string) => void;
  onResume: (id: string) => void;
  onCancel: (id: string) => void;
  onRetry: (id: string) => void;
  onRemove: (id: string) => void;
  onReveal: (filepath: string) => void;
}

export const QueueTab: React.FC<QueueTabProps> = ({
  queueItems,
  darkMode,
  onRefresh,
  onPause,
  onResume,
  onCancel,
  onRetry,
  onRemove,
  onReveal,
}) => {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-base font-semibold">Active & Queued Tasks ({queueItems.length})</h3>
        <button
          type="button"
          onClick={onRefresh}
          className="px-3 py-1 rounded-lg border border-zinc-700/60 hover:bg-zinc-800 text-xs font-medium text-zinc-300 flex items-center gap-1.5"
        >
          <RefreshCw className="w-3 h-3" />
          Refresh Queue
        </button>
      </div>

      {queueItems.length === 0 ? (
        <div className={`p-12 text-center rounded-2xl border ${darkMode ? 'bg-zinc-900/30 border-zinc-800' : 'bg-white border-zinc-200'}`}>
          <ListOrdered className="w-10 h-10 mx-auto mb-3 text-zinc-600" />
          <h4 className="font-medium text-sm">Download Queue Empty</h4>
          <p className="text-xs text-zinc-500 mt-1">Add items from the Downloader to track active and queued tasks.</p>
        </div>
      ) : (
        queueItems.map((item) => (
          <div
            key={item.id}
            className={`p-5 rounded-2xl border space-y-3 ${darkMode ? 'bg-zinc-900/40 border-zinc-800' : 'bg-white border-zinc-200 shadow-sm'}`}
          >
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <h4 className="font-semibold text-sm line-clamp-1">{item.title}</h4>
                <p className="text-xs text-zinc-400 truncate max-w-lg">{item.url}</p>
              </div>

              <div className="flex items-center gap-2">
                <span className={`px-2.5 py-1 rounded-md text-xs font-medium uppercase ${
                  item.state === 'completed' ? 'bg-emerald-500/20 text-emerald-400' :
                  item.state === 'failed' ? 'bg-rose-500/20 text-rose-400' :
                  item.state === 'cancelled' ? 'bg-zinc-800 text-zinc-400' :
                  item.state === 'downloading' ? 'bg-indigo-500/20 text-indigo-400 animate-pulse' :
                  'bg-amber-500/20 text-amber-400'
                }`}>
                  {item.state}
                </span>

                {item.state === 'downloading' && (
                  <button
                    type="button"
                    onClick={() => onPause(item.id)}
                    className="p-1.5 rounded-lg border border-zinc-700/60 hover:bg-zinc-800 text-xs font-medium text-zinc-300"
                    title="Pause Download"
                  >
                    Pause
                  </button>
                )}

                {item.state === 'paused' && (
                  <button
                    type="button"
                    onClick={() => onResume(item.id)}
                    className="p-1.5 rounded-lg border border-zinc-700/60 hover:bg-zinc-800 text-xs font-medium text-zinc-300 flex items-center gap-1"
                    title="Resume Download"
                  >
                    <Play className="w-3 h-3" />
                    Resume
                  </button>
                )}

                {['queued', 'downloading'].includes(item.state) && (
                  <button
                    type="button"
                    onClick={() => onCancel(item.id)}
                    className="p-1.5 rounded-lg border border-zinc-700/60 hover:bg-zinc-800 text-xs font-medium text-zinc-400 hover:text-rose-400"
                    title="Cancel Download"
                  >
                    Cancel
                  </button>
                )}

                {item.state === 'failed' && (
                  <button
                    type="button"
                    onClick={() => onRetry(item.id)}
                    className="p-1.5 rounded-lg border border-zinc-700/60 hover:bg-zinc-800 text-xs font-medium text-amber-400 flex items-center gap-1"
                    title="Retry Download"
                  >
                    <RotateCcw className="w-3 h-3" />
                    Retry
                  </button>
                )}

                {['completed', 'cancelled', 'failed'].includes(item.state) && (
                  <button
                    type="button"
                    onClick={() => onRemove(item.id)}
                    className="p-1.5 rounded-lg hover:bg-zinc-800 text-zinc-500 hover:text-rose-400 transition"
                    title="Delete item"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>

            {/* Progress Bar & Real-time Metrics */}
            <div className="space-y-1.5">
              <div className="w-full bg-zinc-800/80 rounded-full h-2 overflow-hidden">
                <div
                  className={`h-full transition-all duration-300 ${
                    item.state === 'completed' ? 'bg-emerald-500' :
                    item.state === 'failed' ? 'bg-rose-500' :
                    'bg-indigo-500'
                  }`}
                  style={{ width: `${Math.min(100, Math.max(0, item.percent))}%` }}
                />
              </div>

              <div className="flex items-center justify-between text-xs text-zinc-400 font-mono">
                <span>{item.percent.toFixed(1)}%</span>
                <div className="flex items-center gap-4">
                  {item.speed > 0 && <span>{(item.speed / (1024 * 1024)).toFixed(2)} MB/s</span>}
                  {item.eta > 0 && <span>ETA: {item.eta}s</span>}
                  {item.total_bytes > 0 && (
                    <span>
                      {(item.downloaded_bytes / (1024 * 1024)).toFixed(1)} / {(item.total_bytes / (1024 * 1024)).toFixed(1)} MB
                    </span>
                  )}
                </div>
              </div>
            </div>

            {item.error_message && (
              <div className="text-xs text-rose-400 bg-rose-500/10 px-3 py-2 rounded-lg border border-rose-500/20">
                {item.error_message}
              </div>
            )}

            {item.filepath && item.state === 'completed' && (
              <div className="pt-2 border-t border-zinc-800/60 flex items-center justify-between text-xs">
                <span className="text-zinc-500 truncate max-w-md font-mono">{item.filepath}</span>
                <button
                  type="button"
                  onClick={() => onReveal(item.filepath!)}
                  className="px-2.5 py-1 rounded-lg border border-zinc-700/60 hover:bg-zinc-800 text-zinc-300 flex items-center gap-1 transition"
                >
                  <FolderOpen className="w-3.5 h-3.5" />
                  Reveal in Folder
                </button>
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
};
