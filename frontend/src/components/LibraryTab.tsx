import React from 'react';
import { Film, FolderOpen, Trash2 } from 'lucide-react';
import type { QueueItem } from '../types';

interface LibraryTabProps {
  completedJobs: QueueItem[];
  darkMode: boolean;
  onReveal: (filepath: string) => void;
  onRemove: (id: string) => void;
}

export const LibraryTab: React.FC<LibraryTabProps> = ({
  completedJobs,
  darkMode,
  onReveal,
  onRemove,
}) => {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h3 className="text-base font-semibold">Local Media Catalog</h3>
          <p className="text-xs text-zinc-500">Organized local collection with format tags and storage management</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 rounded-lg bg-zinc-900 border border-zinc-800 text-xs font-mono text-zinc-400">
            Storage: Managed Downloads
          </span>
        </div>
      </div>

      {completedJobs.length === 0 ? (
        <div className={`p-12 text-center rounded-2xl border ${darkMode ? 'bg-zinc-900/30 border-zinc-800' : 'bg-white border-zinc-200'}`}>
          <Film className="w-10 h-10 mx-auto mb-3 text-zinc-600" />
          <h4 className="font-medium text-sm">Media Library Empty</h4>
          <p className="text-xs text-zinc-500 mt-1">Downloaded media files are automatically indexed into your local catalog.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {completedJobs.map((job) => (
            <div
              key={job.id}
              className={`p-4 rounded-2xl border flex flex-col justify-between space-y-3 ${
                darkMode ? 'bg-zinc-900/40 border-zinc-800' : 'bg-white border-zinc-200 shadow-sm'
              }`}
            >
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                    {job.format_id || 'Media'}
                  </span>
                  <span className="text-[11px] text-zinc-500 font-mono">
                    {job.total_bytes ? `${(job.total_bytes / (1024 * 1024)).toFixed(1)} MB` : 'Local file'}
                  </span>
                </div>
                <h4 className="font-semibold text-sm line-clamp-2 leading-snug">{job.title}</h4>
                <p className="text-[11px] text-zinc-500 truncate font-mono">{job.filepath || job.url}</p>
              </div>

              <div className="pt-2 border-t border-zinc-800/60 flex items-center justify-between">
                {job.filepath && (
                  <button
                    type="button"
                    onClick={() => onReveal(job.filepath!)}
                    className="px-2.5 py-1 rounded-lg border border-zinc-700/60 hover:bg-zinc-800 text-xs text-zinc-300 font-medium flex items-center gap-1.5 transition"
                  >
                    <FolderOpen className="w-3.5 h-3.5" />
                    Reveal
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => onRemove(job.id)}
                  className="p-1 rounded-lg hover:bg-zinc-800 text-zinc-500 hover:text-rose-400 transition"
                  title="Remove from catalog"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
