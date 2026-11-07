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


def embed_metadata(
    input_file: str,
    title: str | None = None,
    artist: str | None = None,
    thumbnail: str | None = None,
    ffmpeg_bin: str | None = None
) -> str:
    """
    Embed title, artist, and optional thumbnail cover art cleanly.
    """
    input_path = Path(input_file).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input file '{input_file}' not found.")

    bin_path = resolve_ffmpeg_path(ffmpeg_bin)
    output_file = str(input_path.parent / f"{input_path.stem}_meta{input_path.suffix}")

    cmd = [bin_path, "-i", str(input_path), "-y"]

    if title:
        cmd += ["-metadata", f"title={title}"]
    if artist:
        cmd += ["-metadata", f"artist={artist}"]

    if thumbnail:
        thumb_path = Path(thumbnail).resolve()
        if thumb_path.exists():
            cmd += ["-i", str(thumb_path), "-map", "0", "-map", "1", "-c", "copy", "-disposition:v:1", "attached_pic"]

    cmd.append(output_file)

    logger.info(f"Embedding metadata into {input_path.name}")
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    except subprocess.CalledProcessError as exc:
        err_msg = exc.stderr.strip() if exc.stderr else str(exc)
        logger.error(f"FFmpeg metadata embed failed: {err_msg}")
        raise FFmpegExecutionError(f"FFmpeg metadata embed failed: {err_msg}")

    return output_file
