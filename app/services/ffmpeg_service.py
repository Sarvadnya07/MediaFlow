import os
import shutil
import subprocess
from pathlib import Path
from ..config import settings
from ..security import ensure_within_directory, SecurityError
from ..logging_config import logger


class FFmpegResolutionError(RuntimeError):
    pass


class FFmpegExecutionError(RuntimeError):
    pass


def resolve_ffmpeg_path(custom_path: str | None = None) -> str:
    """
    Hierarchical resolution of the FFmpeg binary:
    1. Custom path if provided and executable.
    2. Environment variable FFMPEG_PATH.
    3. System PATH lookup via shutil.which('ffmpeg').
    """
    candidates = []
    if custom_path:
        candidates.append(Path(custom_path))

    env_ffmpeg = os.environ.get("FFMPEG_PATH")
    if env_ffmpeg:
        candidates.append(Path(env_ffmpeg))

    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate.resolve())

    system_which = shutil.which("ffmpeg")
    if system_which:
        return system_which

    raise FFmpegResolutionError(
        "FFmpeg binary not found. Please ensure FFmpeg is installed and added to PATH, "
        "or configure its path in settings."
    )


def resolve_ffprobe_path(custom_path: str | None = None) -> str:
    """
    Hierarchical resolution of the FFprobe binary.
    """
    candidates = []
    if custom_path:
        candidates.append(Path(custom_path))

    env_ffprobe = os.environ.get("FFPROBE_PATH")
    if env_ffprobe:
        candidates.append(Path(env_ffprobe))

    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate.resolve())

    system_which = shutil.which("ffprobe")
    if system_which:
        return system_which

    raise FFmpegResolutionError("FFprobe binary not found on PATH or configured location.")


def convert_to_audio(
    input_file: str,
    output_format: str = "mp3",
    bitrate: str = "192k",
    sample_rate: str = "44100",
    ffmpeg_bin: str | None = None
) -> str:
    """
    Convert a media file to an audio format safely using direct argument lists.
    """
    input_path = Path(input_file).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input file '{input_file}' not found.")

    valid_formats = {"mp3", "m4a", "wav", "flac", "ogg", "aac", "opus"}
    clean_format = output_format.lower().strip(".")
    if clean_format not in valid_formats:
        raise ValueError(f"Unsupported output audio format: {output_format}")

    bin_path = resolve_ffmpeg_path(ffmpeg_bin)
    output_file = str(input_path.with_suffix(f".{clean_format}"))

    cmd = [
        bin_path,
        "-i", str(input_path),
        "-vn",
        "-ab", bitrate,
        "-ar", sample_rate,
        "-y",
        output_file
    ]

    logger.info(f"Executing FFmpeg audio conversion to {clean_format}: {input_path.name}")
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    except subprocess.CalledProcessError as exc:
        err_msg = exc.stderr.strip() if exc.stderr else str(exc)
        logger.error(f"FFmpeg conversion failed: {err_msg}")
        raise FFmpegExecutionError(f"FFmpeg audio conversion failed: {err_msg}")

    return output_file


def reencode_video(
    input_file: str,
    output_format: str = "mp4",
    video_codec: str = "libx264",
    audio_codec: str = "aac",
    ffmpeg_bin: str | None = None
) -> str:
    """
    Re-encode a video file cleanly without shell expansion.
    """
    input_path = Path(input_file).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input video file '{input_file}' not found.")

    valid_formats = {"mp4", "mkv", "webm", "avi", "mov"}
    clean_format = output_format.lower().strip(".")
    if clean_format not in valid_formats:
        raise ValueError(f"Unsupported output video format: {output_format}")

    bin_path = resolve_ffmpeg_path(ffmpeg_bin)
    output_file = str(input_path.parent / f"{input_path.stem}_reencoded.{clean_format}")

    cmd = [
        bin_path,
        "-i", str(input_path),
        "-c:v", video_codec,
        "-c:a", audio_codec,
        "-y",
        output_file
    ]

    logger.info(f"Executing FFmpeg video re-encode: {input_path.name}")
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    except subprocess.CalledProcessError as exc:
        err_msg = exc.stderr.strip() if exc.stderr else str(exc)
        logger.error(f"FFmpeg video re-encode failed: {err_msg}")
        raise FFmpegExecutionError(f"FFmpeg video re-encode failed: {err_msg}")

    return output_file


def verify_media_file(file_path: str, ffprobe_bin: str | None = None) -> dict:
    """
    Validate that a media file exists, has non-zero size, and is a valid media container using ffprobe.
    """
    path = Path(file_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Media file '{file_path}' does not exist.")

    file_size = path.stat().st_size
    if file_size == 0:
        raise ValueError(f"Media file '{file_path}' is empty (0 bytes).")

    probe_bin = resolve_ffprobe_path(ffprobe_bin)
    cmd = [
        probe_bin,
        "-v", "error",
        "-show_entries", "format=format_name,duration,size,bit_rate:stream=codec_type,codec_name,width,height",
        "-of", "json",
        str(path)
    ]

    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        import json
        probe_data = json.loads(res.stdout)
        format_info = probe_data.get("format", {})
        streams = probe_data.get("streams", [])

        has_video = any(s.get("codec_type") == "video" for s in streams)
        has_audio = any(s.get("codec_type") == "audio" for s in streams)

        return {
            "valid": True,
            "filepath": str(path),
            "filesize": file_size,
            "format_name": format_info.get("format_name"),
            "duration": float(format_info.get("duration", 0.0)) if format_info.get("duration") else None,
            "has_video": has_video,
            "has_audio": has_audio,
            "streams_count": len(streams),
        }
    except Exception as exc:
        logger.error(f"Media container validation failed for {file_path}: {str(exc)}")
        raise FFmpegExecutionError(f"Container validation failed: {str(exc)}")
