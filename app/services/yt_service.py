import os
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import yt_dlp
from ..config import settings
from ..security import validate_and_sanitize_url, sanitize_filename, ensure_within_directory
from ..logging_config import logger
from ..engine.protocol import MediaAnalysisResult, MediaFormatInfo


class DownloadCancelledError(Exception):
    """Raised when an ongoing download task is cancelled by user request."""
    pass


# Global registry of active download cancellation events keyed by job_id
_active_cancellations: Dict[str, threading.Event] = {}
_cancellation_lock = threading.Lock()


def register_cancellation_token(job_id: str) -> threading.Event:
    with _cancellation_lock:
        token = threading.Event()
        _active_cancellations[job_id] = token
        return token


def trigger_cancellation(job_id: str) -> bool:
    with _cancellation_lock:
        token = _active_cancellations.get(job_id)
        if token:
            token.set()
            return True
        return False


def unregister_cancellation_token(job_id: str):
    with _cancellation_lock:
        _active_cancellations.pop(job_id, None)


def analyze_url(url: str, allow_private: bool = False) -> MediaAnalysisResult:
    """
    Extract video metadata, format tree, and subtitle streams without downloading.
    Incorporates features from Tkinter prototype (automatic captions and formats list).
    """
    safe_url = validate_and_sanitize_url(url, allow_private=allow_private)

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(safe_url, download=False)
        if not info:
            raise ValueError(f"Unable to extract media information from: {url}")

    # Check for playlists
    is_playlist = info.get("_type") == "playlist"
    if is_playlist:
        entries = list(info.get("entries", []))
        return MediaAnalysisResult(
            url=safe_url,
            extractor=info.get("extractor", "generic"),
            id=str(info.get("id", "")),
            title=info.get("title", "Playlist"),
            description=info.get("description"),
            thumbnail=info.get("thumbnails", [{}])[0].get("url") if info.get("thumbnails") else None,
            is_playlist=True,
            playlist_count=len(entries),
            formats=[],
            subtitles=[],
            automatic_captions=[],
        )

    # Parse and normalize individual stream formats
    raw_formats = info.get("formats", [])
    parsed_formats: List[MediaFormatInfo] = []

    for f in raw_formats:
        vcodec = f.get("vcodec")
        acodec = f.get("acodec")
        has_video = vcodec is not None and vcodec != "none"
        has_audio = acodec is not None and acodec != "none"

        parsed_formats.append(
            MediaFormatInfo(
                format_id=str(f.get("format_id", "")),
                ext=f.get("ext", "mp4"),
                resolution=f.get("resolution") or (f"{f.get('width')}x{f.get('height')}" if f.get("width") and f.get("height") else None),
                width=f.get("width"),
                height=f.get("height"),
                fps=f.get("fps"),
                vcodec=vcodec,
                acodec=acodec,
                filesize=f.get("filesize"),
                filesize_approx=f.get("filesize_approx"),
                tbr=f.get("tbr"),
                format_note=f.get("format_note"),
                has_video=has_video,
                has_audio=has_audio,
            )
        )

    # Subtitles and captions (following Tkinter prototype logic)
    subtitles = list(info.get("subtitles", {}).keys())
    auto_captions = list(info.get("automatic_captions", {}).keys())

    return MediaAnalysisResult(
        url=safe_url,
        extractor=info.get("extractor", "generic"),
        id=str(info.get("id", "")),
        title=info.get("title", "Unknown Title"),
        description=info.get("description"),
        duration=int(info.get("duration", 0)) if info.get("duration") else None,
        uploader=info.get("uploader"),
        thumbnail=info.get("thumbnail"),
        formats=parsed_formats,
        subtitles=subtitles,
        automatic_captions=auto_captions,
        is_playlist=False,
    )


def download_stream(
    url: str,
    output_dir: str | Path,
    job_id: str,
    format_id: Optional[str] = None,
    quality: Optional[str] = None,
    subtitle_lang: Optional[str] = None,
    write_thumbnail: bool = True,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ffmpeg_location: Optional[str] = None,
    allow_private: bool = False,
) -> Dict[str, Any]:
    """
    Download a media stream with real-time cancellation tokens and progress dispatch.
    """
    safe_url = validate_and_sanitize_url(url, allow_private=allow_private)
    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    token = register_cancellation_token(job_id)

    # Format selection strategy
    if format_id:
        format_spec = format_id
    elif quality and quality.endswith("p"):
        height = quality[:-1]
        format_spec = f"bestvideo[height<={height}]+bestaudio/best"
    else:
        format_spec = "bestvideo+bestaudio/best"

    outtmpl = str(out_dir / "%(title)s.%(ext)s")

    def yt_progress_hook(d: Dict[str, Any]):
        if token.is_set():
            raise DownloadCancelledError(f"Job {job_id} was cancelled by user.")

        if progress_callback:
            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                speed = d.get("speed", 0)
                eta = d.get("eta", 0)
                percent_str = d.get("_percent_str", "0%").replace("%", "").strip()
                try:
                    percent = float(percent_str)
                except ValueError:
                    percent = (downloaded / total * 100) if total > 0 else 0.0

                progress_callback({
                    "job_id": job_id,
                    "status": "downloading",
                    "percent": round(percent, 2),
                    "downloaded_bytes": downloaded,
                    "total_bytes": total,
                    "speed": speed,
                    "eta": eta,
                    "filename": d.get("filename"),
                })
            elif status == "finished":
                progress_callback({
                    "job_id": job_id,
                    "status": "processing",
                    "percent": 99.0,
                    "filename": d.get("filename"),
                })

    ydl_opts: Dict[str, Any] = {
        "outtmpl": outtmpl,
        "format": format_spec,
        "merge_output_format": "mp4",
        "progress_hooks": [yt_progress_hook],
        "writethumbnail": write_thumbnail,
        "quiet": True,
        "no_warnings": True,
    }

    if ffmpeg_location:
        ydl_opts["ffmpeg_location"] = ffmpeg_location

    # Subtitles handling
    if subtitle_lang:
        ydl_opts["writesubtitles"] = True
        if subtitle_lang == "generate_auto":
            ydl_opts["writeautomaticsub"] = True
        else:
            ydl_opts["subtitleslangs"] = [subtitle_lang]
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegSubtitlesConvertor",
            "format": "srt",
        }]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(safe_url, download=True)
            title = info.get("title", "Unknown Title")
            filename = ydl.prepare_filename(info)
            description = info.get("description", "")
            duration = int(info.get("duration", 0)) if info.get("duration") else None

            # Check if actual output was merged into mp4
            if not os.path.exists(filename):
                base, _ = os.path.splitext(filename)
                for ext in [".mp4", ".mkv", ".webm"]:
                    candidate = base + ext
                    if os.path.exists(candidate):
                        filename = candidate
                        break

            # Find matching thumbnail
            thumbnail = None
            base, _ = os.path.splitext(filename)
            for ext in [".jpg", ".png", ".webp", ".jpeg"]:
                candidate = base + ext
                if os.path.exists(candidate):
                    thumbnail = candidate
                    break

            # Verify file exists and has non-zero bytes
            if not os.path.exists(filename) or os.path.getsize(filename) == 0:
                raise RuntimeError(f"Download output file '{filename}' was not created or is empty.")

            # Run FFprobe validation if available
            verification_data = None
            try:
                from .ffmpeg_service import verify_media_file
                verification_data = verify_media_file(filename)
            except Exception as v_err:
                logger.warning(f"FFprobe verification skipped/failed: {v_err}")

            return {
                "job_id": job_id,
                "title": title,
                "filepath": filename,
                "filesize": os.path.getsize(filename),
                "thumbnail_path": thumbnail,
                "description": description,
                "duration": duration,
                "status": "completed",
                "verification": verification_data,
            }
    except DownloadCancelledError:
        logger.info(f"Download stream cancelled for job {job_id}")
        raise
    except Exception as exc:
        if token.is_set():
            raise DownloadCancelledError(f"Job {job_id} was cancelled by user.")
        logger.error(f"Download failed for job {job_id}: {str(exc)}")
        raise
    finally:
        unregister_cancellation_token(job_id)
