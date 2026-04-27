import subprocess
import os

def convert_to_audio(input_file: str, output_format: str = "mp3") -> str:
    """
    Convert video file to audio (default mp3).
    """
    base, _ = os.path.splitext(input_file)
    output_file = f"{base}.{output_format}"

    cmd = [
        "ffmpeg",
        "-i", input_file,
        "-vn",               # no video
        "-ab", "192k",       # audio bitrate
        "-ar", "44100",      # audio sample rate
        "-y",                # overwrite
        output_file
    ]

    subprocess.run(cmd, check=True)
    return output_file


def reencode_video(input_file: str, output_format: str = "mp4") -> str:
    """
    Re-encode video to another format.
    """
    base, _ = os.path.splitext(input_file)
    output_file = f"{base}_reencoded.{output_format}"

    cmd = [
        "ffmpeg",
        "-i", input_file,
        "-c:v", "libx264",   # H.264 video
        "-c:a", "aac",       # AAC audio
        "-y",
        output_file
    ]

    subprocess.run(cmd, check=True)
    return output_file


def embed_metadata(input_file: str, title: str = None, artist: str = None, thumbnail: str = None) -> str:
    """
    Embed metadata and optional thumbnail into file.
    """
    base, ext = os.path.splitext(input_file)
    output_file = f"{base}_meta{ext}"

    cmd = ["ffmpeg", "-i", input_file, "-y"]

    if title:
        cmd += ["-metadata", f"title={title}"]
    if artist:
        cmd += ["-metadata", f"artist={artist}"]
    if thumbnail and os.path.exists(thumbnail):
        cmd += ["-i", thumbnail, "-map", "0", "-map", "1", "-c", "copy", "-disposition:v:1", "attached_pic"]

    cmd.append(output_file)

    subprocess.run(cmd, check=True)
    return output_file
