export type ViewMode = 'home' | 'queue' | 'library' | 'history' | 'settings' | 'diagnostics' | 'about';

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'info';
  text: string;
}

export interface HealthStatus {
  status: string;
  dependencies: {
    ffmpeg: boolean | string;
    yt_dlp: boolean | string;
  };
}

export interface FormatOption {
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

export interface AnalysisData {
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
  playlist_count?: number;
}

export interface QueueItem {
  id: string;
  url: string;
  title: string;
  state: 'queued' | 'analyzing' | 'downloading' | 'processing' | 'verifying' | 'completed' | 'paused' | 'failed' | 'cancelled';
  format_id?: string;
  percent: number;
  downloaded_bytes: number;
  total_bytes: number;
  speed: number;
  eta: number;
  filepath?: string;
  error_message?: string;
  retry_count: number;
  created_at: number;
}
