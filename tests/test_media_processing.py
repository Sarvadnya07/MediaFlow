import os
import pytest
from pathlib import Path
from app.services import ffmpeg_service
from app.services.ffmpeg_service import (
    FFmpegResolutionError,
    FFmpegExecutionError,
    get_ffmpeg_capabilities,
    convert_to_audio,
    verify_media_file,
)


def test_ffmpeg_binary_discovery_and_capabilities():
    caps = get_ffmpeg_capabilities()
    assert caps["available"] is True
    assert "version" in caps
    assert len(caps["supported_audio_formats"]) > 0
    assert "mp3" in caps["supported_audio_formats"]
    assert "wav" in caps["supported_audio_formats"]


def test_missing_ffmpeg_binary_handling():
    with pytest.raises(FFmpegResolutionError):
        ffmpeg_service.resolve_ffmpeg_path("C:/nonexistent_path/ffmpeg_fake.exe")


def test_invalid_audio_format_rejection(tmp_path):
    dummy_input = tmp_path / "dummy.mp4"
    dummy_input.write_bytes(b"dummy")

    with pytest.raises(ValueError, match="Unsupported output audio format"):
        convert_to_audio(str(dummy_input), output_format="xyz123_invalid")


def test_audio_conversion_and_cleanup_on_failure(tmp_path):
    # An invalid input file should fail conversion cleanly and clean up any .tmp files
    corrupted_file = tmp_path / "corrupted.mp4"
    corrupted_file.write_bytes(b"not a valid media stream")

    with pytest.raises(FFmpegExecutionError):
        convert_to_audio(str(corrupted_file), output_format="mp3")

    # Verify no dangling temporary files remain
    tmp_files = list(tmp_path.glob("*.tmp.*"))
    assert len(tmp_files) == 0


def test_real_audio_conversion_from_valid_source(tmp_path):
    """
    Convert a minimal synthesized WAV audio file to MP3 and verify the result using verify_media_file.
    """
    import wave

    wav_path = tmp_path / "test_tone.wav"
    # Generate 1-second 44.1kHz silent WAV file
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(b"\x00\x00" * 44100)

    assert wav_path.exists()

    # Convert to MP3
    mp3_output = convert_to_audio(
        input_file=str(wav_path),
        output_format="mp3",
        bitrate="128k",
    )

    assert os.path.exists(mp3_output)
    assert mp3_output.endswith(".mp3")
    assert os.path.getsize(mp3_output) > 0

    # Verify converted container via FFprobe
    verification = verify_media_file(mp3_output)
    assert verification["valid"] is True
    assert verification["has_audio"] is True
    assert "mp3" in verification["format_name"]
