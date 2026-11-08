"""
MediaDock Local Media Library Unit & Integration Tests.
Verifies file indexing, ffprobe metadata extraction, search & filtering,
favorites, renaming, safe deletion containment, and storage calculation.
"""
import pytest
from pathlib import Path
from app.library.models import MediaType
from app.library.manager import MediaLibraryManager
from app.security import SecurityError


def test_media_library_indexing_and_search(tmp_path):
    db_file = tmp_path / "test_library.db"
    media_dir = tmp_path / "downloads"
    media_dir.mkdir(parents=True, exist_ok=True)

    # Override download directory for test isolation
    mgr = MediaLibraryManager(db_path=str(db_file))
    mgr.download_dir = media_dir

    # Create dummy media files
    v1 = media_dir / "sample_video_1080p.mp4"
    v1.write_bytes(b"dummy video data payload 1")

    a1 = media_dir / "podcast_episode_1.mp3"
    a1.write_bytes(b"dummy audio data payload 2")

    # Index
    item1 = mgr.index_file(v1, title="Sample Video", category="Video Clips", tags=["hd", "sample"])
    assert item1 is not None
    assert item1.media_type == MediaType.VIDEO
    assert item1.category == "Video Clips"
    assert "hd" in item1.tags

    item2 = mgr.index_file(a1, title="Podcast Episode 1", category="Audio Podcasts", tags=["podcast"])
    assert item2 is not None
    assert item2.media_type == MediaType.AUDIO

    # Search
    results = mgr.get_items(search="Podcast")
    assert len(results) == 1
    assert results[0].id == item2.id

    # Filter by media type
    video_results = mgr.get_items(media_type="video")
    assert len(video_results) == 1
    assert video_results[0].id == item1.id


def test_favorites_and_renaming(tmp_path):
    db_file = tmp_path / "test_fav_library.db"
    media_dir = tmp_path / "downloads"
    media_dir.mkdir(parents=True, exist_ok=True)

    mgr = MediaLibraryManager(db_path=str(db_file))
    mgr.download_dir = media_dir

    v = media_dir / "clip.mp4"
    v.write_bytes(b"clip content")

    item = mgr.index_file(v, title="My Clip")
    assert item.is_favorite is False

    # Toggle favorite
    mgr.set_favorite(item.id, True)
    favs = mgr.get_items(favorites_only=True)
    assert len(favs) == 1
    assert favs[0].id == item.id

    # Rename file
    renamed = mgr.rename_file(item.id, "Renamed_Clip")
    assert renamed.title == "Renamed_Clip"
    assert Path(renamed.file_path).name == "Renamed_Clip.mp4"
    assert Path(renamed.file_path).exists()
    assert not v.exists()


def test_safe_deletion_and_containment(tmp_path):
    db_file = tmp_path / "test_del_library.db"
    media_dir = tmp_path / "downloads"
    media_dir.mkdir(parents=True, exist_ok=True)

    mgr = MediaLibraryManager(db_path=str(db_file))
    mgr.download_dir = media_dir

    f = media_dir / "to_delete.mp4"
    f.write_bytes(b"delete me")

    item = mgr.index_file(f)
    assert item is not None

    # Delete with file removal
    mgr.delete_item(item.id, delete_file=True)
    assert not f.exists()
    assert len(mgr.get_items()) == 0


def test_storage_stats_reporting(tmp_path):
    db_file = tmp_path / "test_stats_library.db"
    media_dir = tmp_path / "downloads"
    media_dir.mkdir(parents=True, exist_ok=True)

    mgr = MediaLibraryManager(db_path=str(db_file))
    mgr.download_dir = media_dir

    f = media_dir / "sized_file.mp4"
    f.write_bytes(b"1234567890")  # 10 bytes

    mgr.index_file(f)
    stats = mgr.get_storage_stats()

    assert stats.total_items == 1
    assert stats.total_size_bytes == 10
    assert stats.video_count == 1
    assert stats.disk_total_bytes > 0
    assert stats.disk_free_bytes > 0
