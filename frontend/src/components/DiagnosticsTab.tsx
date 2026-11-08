import React from 'react';
import { Cpu, HardDrive, ShieldCheck } from 'lucide-react';
import type { HealthStatus, QueueItem } from '../types';

interface DiagnosticsTabProps {
  darkMode: boolean;
  health: HealthStatus | null;
  capabilities: any;
  queueItems: QueueItem[];
  completedJobsCount: number;
}

export const DiagnosticsTab: React.FC<DiagnosticsTabProps> = ({
  darkMode,
  health,
  capabilities,
  queueItems,
  completedJobsCount,
}) => {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className={`p-5 rounded-2xl border ${darkMode ? 'bg-zinc-900/40 border-zinc-800' : 'bg-white border-zinc-200'}`}>
          <div className="flex items-center gap-2 mb-3 text-indigo-400">
            <Cpu className="w-5 h-5" />
            <h4 className="font-semibold text-sm">Python Engine Sidecar</h4>
          </div>
          <div className="space-y-1.5 text-xs text-zinc-400">
            <p>Communication: <span className="text-emerald-400 font-mono">Stdio JSON Lines</span></p>
            <p>Health Status: <span className="text-emerald-400 font-medium">{health?.status || 'Checking...'}</span></p>
            <p>FFmpeg: <span className="text-emerald-400">{String(health?.dependencies?.ffmpeg)}</span></p>
            <p>yt-dlp: <span className="text-emerald-400">{String(health?.dependencies?.yt_dlp)}</span></p>
            <p>Active Thread Workers: <span className="text-zinc-200">{queueItems.filter((i) => i.state === 'downloading').length}</span></p>
          </div>
        </div>

        <div className={`p-5 rounded-2xl border ${darkMode ? 'bg-zinc-900/40 border-zinc-800' : 'bg-white border-zinc-200'}`}>
          <div className="flex items-center gap-2 mb-3 text-indigo-400">
            <HardDrive className="w-5 h-5" />
            <h4 className="font-semibold text-sm">Persistence & Cache</h4>
          </div>
          <div className="space-y-1.5 text-xs text-zinc-400">
            <p>Database: <span className="text-zinc-200">SQLite 3 (WAL mode enabled)</span></p>
            <p>Queued / Active Tasks: <span className="text-zinc-200">{queueItems.length}</span></p>
            <p>Completed History: <span className="text-emerald-400 font-medium">{completedJobsCount}</span></p>
            <p>Isolation: <span className="text-emerald-400 font-medium">Local Sandboxed Stdio</span></p>
          </div>
        </div>
      </div>

      {capabilities?.ffmpeg && (
        <div className={`p-5 rounded-2xl border space-y-2 ${darkMode ? 'bg-zinc-900/40 border-zinc-800' : 'bg-white border-zinc-200'}`}>
          <div className="flex items-center gap-2 text-indigo-400">
            <ShieldCheck className="w-5 h-5" />
            <h4 className="font-semibold text-sm">FFmpeg Encoder Diagnostics</h4>
          </div>
          <p className="text-xs text-zinc-400">
            Version: <span className="text-zinc-200">{capabilities.ffmpeg.version}</span> &bull; Binary: <span className="text-zinc-200 font-mono">{capabilities.ffmpeg.binary_path}</span>
          </p>
          <p className="text-xs text-zinc-400">
            Detected Audio Codecs: <span className="text-zinc-300">{capabilities.ffmpeg.supported_audio_formats?.join(', ')}</span>
          </p>
        </div>
      )}
    </div>
  );
};
