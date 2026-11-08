import React from 'react';
import { DownloadCloud } from 'lucide-react';

interface AboutTabProps {
  darkMode: boolean;
}

export const AboutTab: React.FC<AboutTabProps> = ({ darkMode }) => {
  return (
    <div className={`p-6 rounded-2xl border space-y-4 ${darkMode ? 'bg-zinc-900/40 border-zinc-800' : 'bg-white border-zinc-200'}`}>
      <div className="flex items-center gap-3">
        <div className="p-3 rounded-2xl bg-indigo-600 text-white shadow-lg shadow-indigo-600/30">
          <DownloadCloud className="w-6 h-6" />
        </div>
        <div>
          <h3 className="text-base font-bold">MediaDock Desktop</h3>
          <p className="text-xs text-zinc-500">Version 0.1.0-alpha &bull; Production Architecture</p>
        </div>
      </div>

      <p className="text-xs text-zinc-400 leading-relaxed max-w-2xl">
        MediaDock is a modern, high-performance desktop media manager combining Tauri 2 + Rust, React 19, TypeScript, and Python's `yt-dlp` media extraction engine.
      </p>

      <div className="grid grid-cols-2 gap-4 pt-2 text-xs text-zinc-400 max-w-md">
        <div>
          <span className="text-zinc-500 block">Desktop Host</span>
          <span className="text-zinc-200">Tauri 2 + Rust</span>
        </div>
        <div>
          <span className="text-zinc-500 block">User Interface</span>
          <span className="text-zinc-200">React 19 + Tailwind CSS</span>
        </div>
        <div>
          <span className="text-zinc-500 block">Media Engine</span>
          <span className="text-zinc-200">Python 3 + yt-dlp</span>
        </div>
        <div>
          <span className="text-zinc-500 block">Media Transcoding</span>
          <span className="text-zinc-200">FFmpeg 7.1 + FFprobe</span>
        </div>
      </div>
    </div>
  );
};
