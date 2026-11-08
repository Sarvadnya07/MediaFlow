"""
MediaDock Provider Framework Unit and Integration Tests.
Verifies provider contract, URL matching, capability reporting, and direct provider execution.
"""
import pytest
from pathlib import Path
from app.providers.base import BaseProvider, ProviderInfo, ProviderCapability
from app.providers.direct import DirectHttpProvider
from app.providers.ytdlp import YtDlpProvider
from app.providers.registry import ProviderRegistry, provider_registry
from app.services.yt_service import analyze_url, download_stream


def test_provider_registry_discovery():
    reg = ProviderRegistry()
    providers = reg.list_providers()
    assert len(providers) >= 2

    provider_ids = [p.id for p in providers]
    assert "direct_http" in provider_ids
    assert "ytdlp_universal" in provider_ids


def test_provider_url_matching_priority():
    reg = ProviderRegistry()

    # Direct media URL must match direct_http provider
    direct_match = reg.get_provider_for_url("https://example.com/media/audio.mp3")
    assert direct_match is not None
    assert direct_match.info.id == "direct_http"

    # Streaming/generic video URL should match ytdlp provider
    yt_match = reg.get_provider_for_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert yt_match is not None
    assert yt_match.info.id == "ytdlp_universal"


def test_direct_http_provider_capabilities():
    p = DirectHttpProvider()
    assert p.info.capabilities.video is True
    assert p.info.capabilities.audio is True
    assert p.info.capabilities.playlists is False
    assert p.matches_url("https://files.test.org/sample.mp4") is True
    assert p.matches_url("https://files.test.org/sample.unknown") is False


@pytest.mark.network
def test_direct_http_provider_analyze_and_download(tmp_path):
    # Create a small local test file served as direct URL simulated
    p = DirectHttpProvider()
    test_url = "https://interactive-examples.mdn.mozilla.net/media/cc0-audio/t-rex-roar.mp3"

    # Analyze
    analysis = p.analyze(test_url)
    assert analysis.title == "t-rex-roar"
    assert len(analysis.formats) > 0
    assert analysis.formats[0].ext == "mp3"

    # Download
    progress_records = []
    def on_progress(p_data):
        progress_records.append(p_data)

    res = p.download(
        url=test_url,
        output_dir=str(tmp_path),
        progress_hook=on_progress,
        job_id="test-provider-job"
    )

    out_file = Path(res["filename"])
    assert out_file.exists()
    assert out_file.stat().st_size > 0
    assert len(progress_records) > 0
    assert progress_records[-1]["status"] == "finished"
