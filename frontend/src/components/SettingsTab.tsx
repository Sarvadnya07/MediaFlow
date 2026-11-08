import React from 'react';

interface SettingsFormState {
  downloadDir: string;
  maxConcurrent: number;
  autoConvertAudio: boolean;
  defaultAudioFormat: string;
  embedSubtitles: boolean;
}

interface SettingsTabProps {
  darkMode: boolean;
  settingsForm: SettingsFormState;
  onSettingsChange: (newSettings: SettingsFormState) => void;
  onSave: () => void;
}

export const SettingsTab: React.FC<SettingsTabProps> = ({
  darkMode,
  settingsForm,
  onSettingsChange,
  onSave,
}) => {
  return (
    <div className={`p-6 rounded-2xl border space-y-6 ${darkMode ? 'bg-zinc-900/30 border-zinc-800' : 'bg-white border-zinc-200'}`}>
      <div className="border-b border-zinc-800/80 pb-4 flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold">Preferences & Configuration</h3>
          <p className="text-xs text-zinc-500">Configure storage, concurrent quotas, and media post-processing.</p>
        </div>
        <button
          type="button"
          onClick={onSave}
          className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs transition"
        >
          Save Settings
        </button>
      </div>

      <div className="grid grid-cols-2 gap-6 text-xs">
        <div className="space-y-4">
          <div>
            <label className="block font-medium text-zinc-400 mb-1">Default Download Folder</label>
            <input
              type="text"
              value={settingsForm.downloadDir}
              onChange={(e) => onSettingsChange({ ...settingsForm, downloadDir: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 text-xs text-zinc-200 outline-none"
            />
          </div>
          <div>
            <label className="block font-medium text-zinc-400 mb-1">Max Concurrent Downloads</label>
            <input
              type="number"
              min={1}
              max={10}
              value={settingsForm.maxConcurrent}
              onChange={(e) => onSettingsChange({ ...settingsForm, maxConcurrent: parseInt(e.target.value) || 1 })}
              className="w-32 px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 text-xs text-zinc-200 outline-none"
            />
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block font-medium text-zinc-400 mb-1">Default Audio Extraction Format</label>
            <select
              value={settingsForm.defaultAudioFormat}
              onChange={(e) => onSettingsChange({ ...settingsForm, defaultAudioFormat: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 text-xs text-zinc-200 outline-none"
            >
              <option value="mp3">MP3 (High compatibility, 192kbps)</option>
              <option value="m4a">M4A / AAC (Apple devices standard)</option>
              <option value="flac">FLAC (Lossless audio compression)</option>
              <option value="opus">Opus (Modern high efficiency)</option>
              <option value="wav">WAV (Uncompressed PCM audio)</option>
            </select>
          </div>

          <div className="pt-2 space-y-2">
            <label className="flex items-center gap-2 cursor-pointer text-zinc-300">
              <input
                type="checkbox"
                checked={settingsForm.embedSubtitles}
                onChange={(e) => onSettingsChange({ ...settingsForm, embedSubtitles: e.target.checked })}
                className="rounded border-zinc-800"
              />
              <span>Automatically embed subtitles when available</span>
            </label>
          </div>
        </div>
      </div>
    </div>
  );
};
