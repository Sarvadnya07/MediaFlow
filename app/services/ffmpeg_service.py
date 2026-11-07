import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from ..logging_config import logger
from ..security import ensure_within_directory, SecurityError


class FFmpegResolutionError(RuntimeError):
    pass


class FFmpegExecutionError(RuntimeError):
    pass


def resolve_ffmpeg_path(custom_path: Optional[str] = None) -> str:
    """
    Hierarchical resolution of the FFmpeg binary:
    1. Custom path if provided (must exist and be executable, otherwise raises).
    2. Environment variable FFMPEG_PATH.
    3. System PATH lookup via shutil.which('ffmpeg').
    """
    if custom_path:
        p = Path(custom_path)
        if p.is_file() and os.access(p, os.X_OK):
            return str(p.resolve())
        raise FFmpegResolutionError(f"Configured custom FFmpeg binary not found or not executable: {custom_path}")

    env_ffmpeg = os.environ.get("FFMPEG_PATH")
    if env_ffmpeg:
        p = Path(env_ffmpeg)
        if p.is_file() and os.access(p, os.X_OK):
            return str(p.resolve())

    system_which = shutil.which("ffmpeg")
    if system_which:
        return system_which

    raise FFmpegResolutionError(
        "FFmpeg binary not found. Please ensure FFmpeg is installed and added to PATH, "
        "or configure its path in settings."
    )


def resolve_ffprobe_path(custom_path: Optional[str] = None) -> str:
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


def get_ffmpeg_capabilities(custom_ffmpeg: Optional[str] = None) -> Dict[str, any]:
    """
    Query FFmpeg for its installed version, available encoders, and supported formats.
    """
    try:
        bin_path = resolve_ffmpeg_path(custom_ffmpeg)
    except FFmpegResolutionError as e:
        return {
            "available": False,
            "error": str(e),
            "version": None,
            "audio_encoders": [],
            "video_encoders": [],
        }

    # Query version
    version_str = "Unknown"
    try:
        ver_proc = subprocess.run([bin_path, "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        first_line = ver_proc.stdout.splitlines()[0] if ver_proc.stdout else ""
        match = re.search(r"ffmpeg version\s+([^\s]+)", first_line)
        if match:
            version_str = match.group(1)
        else:
            version_str = first_line[:50]
    except Exception:
        pass

    # Query encoders
    audio_encoders = []
    video_encoders = []
    try:
        enc_proc = subprocess.run([bin_path, "-encoders"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        for line in enc_proc.stdout.splitlines():
            line_str = line.strip()
            if line_str.startswith("A"):  # Audio encoder
                parts = line_str.split()
                if len(parts) >= 2:
                    audio_encoders.append(parts[1])
            elif line_str.startswith("V"):  # Video encoder
                parts = line_str.split()
                if len(parts) >= 2:
                    video_encoders.append(parts[1])
    except Exception:
        # Fallback to standard widely-supported list
        audio_encoders = ["libmp3lame", "aac", "flac", "libopus", "pcm_s16le"]
        video_encoders = ["libx264", "libvpx-vp9"]

    # Normalize supported output audio formats based on detected encoders
    supported_audio = ["wav"]  # Always supported (pcm_s16le)
    if any("mp3" in e or "lame" in e for e in audio_encoders): supported_audio.append("mp3")
    if any("aac" in e for e in audio_encoders): supported_audio.extend(["m4a", "aac"])
    if any("flac" in e for e in audio_encoders): supported_audio.append("flac")
    if any("opus" in e for e in audio_encoders): supported_audio.append("opus")
    if any("vorbis" in e for e in audio_encoders): supported_audio.append("ogg")

    return {
        "available": True,
        "binary_path": bin_path,
        "version": version_str,
        "supported_audio_formats": supported_audio,
        "audio_encoders": audio_encoders[:20],
        "video_encoders": video_encoders[:20],
    }


def convert_to_audio(
    input_file: str,
    output_format: str = "mp3",
    bitrate: str = "192k",
    sample_rate: str = "44100",
    ffmpeg_bin: Optional[str] = None,
    timeout_seconds: int = 300,
) -> str:
    """
    Convert video or audio input to the requested audio format with strict argument construction,
    process timeout, temporary file atomic swap, and verification.
    """
    input_path = Path(input_file).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input file '{input_file}' not found.")

    valid_formats = {"mp3", "m4a", "wav", "flac", "ogg", "aac", "opus"}
    clean_format = output_format.lower().strip(".")
    if clean_format not in valid_formats:
        raise ValueError(f"Unsupported output audio format: {output_format}. Supported: {sorted(valid_formats)}")

    bin_path = resolve_ffmpeg_path(ffmpeg_bin)
    output_file = input_path.with_suffix(f".{clean_format}")
    temp_output = input_path.with_suffix(f".tmp.{clean_format}")

    # Build format-specific encoder arguments
    encoder_args = []
    if clean_format == "mp3":
        encoder_args = ["-c:a", "libmp3lame", "-b:a", bitrate]
    elif clean_format in ("m4a", "aac"):
        encoder_args = ["-c:a", "aac", "-b:a", bitrate]
    elif clean_format == "flac":
        encoder_args = ["-c:a", "flac"]
    elif clean_format == "opus":
        encoder_args = ["-c:a", "libopus", "-b:a", bitrate]
    elif clean_format == "ogg":
        encoder_args = ["-c:a", "libvorbis", "-q:a", "5"]
    elif clean_format == "wav":
        encoder_args = ["-c:a", "pcm_s16le"]

    cmd = [
        bin_path,
        "-i", str(input_path),
        "-vn",
        *encoder_args,
        "-ar", sample_rate,
        "-y",
        str(temp_output),
    ]

    logger.info(f"Executing FFmpeg audio conversion to {clean_format}: {input_path.name}")
    try:
        subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            timeout=timeout_seconds,
        )

        # Atomic rename after successful conversion
        if temp_output.exists():
            temp_output.replace(output_file)

        # Verify output exists and is non-zero
        if not output_file.exists() or output_file.stat().st_size == 0:
            raise FFmpegExecutionError(f"Converted file '{output_file}' is missing or 0 bytes.")

        return str(output_file)

    except subprocess.TimeoutExpired:
        if temp_output.exists():
            temp_output.unlink(missing_ok=True)
        raise TimeoutError(f"FFmpeg conversion timed out after {timeout_seconds} seconds.")

    except subprocess.CalledProcessError as exc:
        if temp_output.exists():
            temp_output.unlink(missing_ok=True)
        err_msg = exc.stderr.strip() if exc.stderr else str(exc)
        logger.error(f"FFmpeg audio conversion failed: {err_msg}")
        raise FFmpegExecutionError(f"FFmpeg conversion failed: {err_msg}")

    except Exception:
        if temp_output.exists():
            temp_output.unlink(missing_ok=True)
        raise


def verify_media_file(file_path: str, ffprobe_bin: Optional[str] = None) -> dict:
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
        str(path),
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
