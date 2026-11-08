import React from 'react';
import { History, Search, FolderOpen, Trash2 } from 'lucide-react';
import { QueueItem } from '../types';

interface HistoryTabProps {
  completedJobs: QueueItem[];
  darkMode: boolean;
  search: string;
  onSearchChange: (val: string) => void;
  onReveal: (filepath: string) => void;
  onRemove: (id: string) => void;
}

export const HistoryTab: React.FC<HistoryTabProps> = ({
  completedJobs,
  darkMode,
  search,
  onSearchChange,
  onReveal,
  onRemove,
}) => {
  const filtered = completedJobs.filter((job) =>
    (job.title || '').toLowerCase().includes(search.toLowerCase()) ||
    (job.url || '').toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-base font-semibold">Completed Downloads ({completedJobs.length})</h3>
        <div className="relative w-64">
          <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-zinc-500" />
          <input
            type="text"
            placeholder="Search history..."
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-zinc-900 border border-zinc-800 text-xs text-zinc-200 outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className={`p-12 text-center rounded-2xl border ${darkMode ? 'bg-zinc-900/30 border-zinc-800' : 'bg-white border-zinc-200'}`}>
          <History className="w-10 h-10 mx-auto mb-3 text-zinc-600" />
          <h4 className="font-medium text-sm">No Download History Found</h4>
          <p className="text-xs text-zinc-500 mt-1">Completed media downloads will appear here with location info.</p>
        </div>
      ) : (
        filtered.map((job) => (
          <div
            key={job.id}
            className={`p-4 rounded-2xl border flex items-center justify-between ${darkMode ? 'bg-zinc-900/30 border-zinc-800' : 'bg-white border-zinc-200 shadow-sm'}`}
          >
            <div className="space-y-1 max-w-lg">
              <h4 className="font-semibold text-sm line-clamp-1">{job.title}</h4>
              <p className="text-xs text-zinc-400 truncate">{job.filepath || job.url}</p>
            </div>

            <div className="flex items-center gap-2">
              {job.filepath && (
                <button
                  type="button"
                  onClick={() => onReveal(job.filepath!)}
                  className="px-3 py-1.5 rounded-lg border border-zinc-700/60 hover:bg-zinc-800 text-xs text-zinc-300 font-medium flex items-center gap-1.5 transition"
                >
                  <FolderOpen className="w-3.5 h-3.5" />
                  Reveal in Folder
                </button>
              )}
              <button
                type="button"
                onClick={() => onRemove(job.id)}
                className="p-1.5 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-rose-400 transition"
                title="Delete from history"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  );
};
