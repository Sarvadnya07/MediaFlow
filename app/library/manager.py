"""
MediaDock Local Media Library Manager.
Handles cataloging, search, tags, favorites, collections, reindexing,
safe file mutations (rename/delete/move), and accurate disk usage reporting.
"""
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.logging_config import logger
from app.security import ensure_within_directory, sanitize_filename, SecurityError
from app.services import ffmpeg_service
from app.library.models import Base, MediaItem, MediaItemRecord, MediaType, LibraryStats


class MediaLibraryManager:
    VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv"}
    AUDIO_EXTENSIONS = {".mp3", ".m4a", ".aac", ".flac", ".wav", ".ogg", ".opus"}

    def __init__(self, db_path: Optional[str] = None):
        database_url = f"sqlite:///{db_path}" if db_path else settings.DATABASE_URL
        self.engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.download_dir = Path(settings.DOWNLOADS_DIR).resolve()
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def _determine_media_type(self, ext: str) -> MediaType:
        ext_lower = ext.lower()
        if ext_lower in self.VIDEO_EXTENSIONS:
            return MediaType.VIDEO
        elif ext_lower in self.AUDIO_EXTENSIONS:
            return MediaType.AUDIO
        return MediaType.UNKNOWN

    def index_file(
        self,
        file_path: str | Path,
        source_url: Optional[str] = None,
        title: Optional[str] = None,
        uploader: Optional[str] = None,
        category: str = "General",
        tags: Optional[List[str]] = None,
    ) -> Optional[MediaItem]:
        """Index a single local file into the media library catalog."""
        path_obj = Path(file_path).resolve()
        if not path_obj.exists() or not path_obj.is_file():
            return None

        # Verify containment inside managed download directory
        ensure_within_directory(path_obj, self.download_dir)

        stat = path_obj.stat()
        file_size = stat.st_size
        ext = path_obj.suffix.lower()
        media_type = self._determine_media_type(ext)

        # Probe file with ffprobe for accurate duration, format and resolution
        probe_meta = {}
        try:
            probe_meta = ffmpeg_service.verify_media_file(str(path_obj))
        except Exception:
            pass

        duration = probe_meta.get("duration") or 0.0
        resolution = None
        if probe_meta.get("width") and probe_meta.get("height"):
            resolution = f"{probe_meta['width']}x{probe_meta['height']}"

        item_id = f"med-{uuid.uuid4().hex[:10]}"
        item_title = title or path_obj.stem
        tags_str = ",".join(tags) if tags else ""

        with self.SessionLocal() as session:
            # Check if file already indexed
            record = session.query(MediaItemRecord).filter(MediaItemRecord.file_path == str(path_obj)).first()
            if record:
                record.title = item_title
                record.file_size = file_size
                record.duration = duration
                record.resolution = resolution
                record.is_missing = False
                record.last_accessed = time.time()
                session.commit()
                return self._record_to_item(record)

            record = MediaItemRecord(
                id=item_id,
                title=item_title,
                file_path=str(path_obj),
                media_type=media_type.value,
                format=ext.lstrip("."),
                resolution=resolution,
                duration=duration,
                file_size=file_size,
                source_url=source_url,
                uploader=uploader,
                category=category,
                tags=tags_str,
                is_favorite=False,
                is_missing=False,
                created_at=stat.st_ctime,
                last_accessed=time.time(),
            )
            session.add(record)
            session.commit()
            return self._record_to_item(record)

    def reindex_directory(self) -> Dict[str, int]:
        """Scan managed downloads directory, reindex new files, and mark removed files as missing."""
        added = 0
        updated = 0
        missing = 0

        existing_on_disk = set()
        for root, _, files in os.walk(self.download_dir):
            for f in files:
                ext = Path(f).suffix.lower()
                if ext in self.VIDEO_EXTENSIONS or ext in self.AUDIO_EXTENSIONS:
                    full_p = Path(root) / f
                    existing_on_disk.add(str(full_p.resolve()))

        with self.SessionLocal() as session:
            records = session.query(MediaItemRecord).all()
            indexed_paths = {r.file_path: r for r in records}

            # Check for missing
            for p_str, r in indexed_paths.items():
                if p_str not in existing_on_disk:
                    if not r.is_missing:
                        r.is_missing = True
                        missing += 1
                else:
                    if r.is_missing:
                        r.is_missing = False
                        updated += 1
            session.commit()

        # Add newly found files
        for p_str in existing_on_disk:
            if p_str not in indexed_paths:
                if self.index_file(p_str):
                    added += 1

        return {"added": added, "updated": updated, "missing": missing}

    def get_items(
        self,
        search: Optional[str] = None,
        media_type: Optional[str] = None,
        category: Optional[str] = None,
        collection: Optional[str] = None,
        favorites_only: bool = False,
        sort_by: str = "created_at",
        sort_desc: bool = True,
    ) -> List[MediaItem]:
        with self.SessionLocal() as session:
            q = session.query(MediaItemRecord).filter(MediaItemRecord.is_missing == False)

            if media_type and media_type != "all":
                q = q.filter(MediaItemRecord.media_type == media_type)

            if category and category != "all":
                q = q.filter(MediaItemRecord.category == category)

            if collection:
                q = q.filter(MediaItemRecord.collection_name == collection)

            if favorites_only:
                q = q.filter(MediaItemRecord.is_favorite == True)

            if search:
                term = f"%{search.strip().lower()}%"
                q = q.filter(
                    (MediaItemRecord.title.ilike(term)) |
                    (MediaItemRecord.uploader.ilike(term)) |
                    (MediaItemRecord.tags.ilike(term))
                )

            # Sorting
            sort_col = getattr(MediaItemRecord, sort_by, MediaItemRecord.created_at)
            if sort_desc:
                q = q.order_by(sort_col.desc())
            else:
                q = q.order_by(sort_col.asc())

            records = q.all()
            return [self._record_to_item(r) for r in records]

    def set_favorite(self, item_id: str, is_favorite: bool) -> bool:
        with self.SessionLocal() as session:
            record = session.query(MediaItemRecord).filter(MediaItemRecord.id == item_id).first()
            if record:
                record.is_favorite = is_favorite
                session.commit()
                return True
        return False

    def update_tags(self, item_id: str, tags: List[str]) -> bool:
        with self.SessionLocal() as session:
            record = session.query(MediaItemRecord).filter(MediaItemRecord.id == item_id).first()
            if record:
                record.tags = ",".join(tags)
                session.commit()
                return True
        return False

    def rename_file(self, item_id: str, new_stem: str) -> MediaItem:
        """Safely rename a library file and update its catalog metadata."""
        safe_name = sanitize_filename(new_stem)
        with self.SessionLocal() as session:
            record = session.query(MediaItemRecord).filter(MediaItemRecord.id == item_id).first()
            if not record:
                raise ValueError(f"Media item {item_id} not found.")

            current_p = Path(record.file_path).resolve()
            ensure_within_directory(current_p, self.download_dir)

            new_p = current_p.parent / f"{safe_name}{current_p.suffix}"
            ensure_within_directory(new_p, self.download_dir)

            if new_p.exists() and new_p != current_p:
                raise FileExistsError(f"Target file {new_p.name} already exists.")

            if current_p.exists():
                current_p.rename(new_p)

            record.title = safe_name
            record.file_path = str(new_p)
            record.last_accessed = time.time()
            session.commit()
            return self._record_to_item(record)

    def delete_item(self, item_id: str, delete_file: bool = True) -> bool:
        """Remove item from catalog and optionally delete file strictly within download directory."""
        with self.SessionLocal() as session:
            record = session.query(MediaItemRecord).filter(MediaItemRecord.id == item_id).first()
            if not record:
                return False

            file_p = Path(record.file_path).resolve()
            if delete_file and file_p.exists():
                # Enforce containment security check before file deletion
                ensure_within_directory(file_p, self.download_dir)
                try:
                    file_p.unlink()
                except Exception as e:
                    logger.error(f"Failed to delete file {file_p}: {e}")
                    raise

            session.delete(record)
            session.commit()
            return True

    def get_storage_stats(self) -> LibraryStats:
        """Calculate accurate on-disk storage statistics without fabrication."""
        total_size = 0
        video_count = 0
        video_size = 0
        audio_count = 0
        audio_size = 0
        fav_count = 0
        categories: Dict[str, int] = {}

        with self.SessionLocal() as session:
            records = session.query(MediaItemRecord).filter(MediaItemRecord.is_missing == False).all()
            for r in records:
                size = r.file_size or 0
                total_size += size
                cat = r.category or "General"
                categories[cat] = categories.get(cat, 0) + size

                if r.media_type == MediaType.VIDEO.value:
                    video_count += 1
                    video_size += size
                elif r.media_type == MediaType.AUDIO.value:
                    audio_count += 1
                    audio_size += size

                if r.is_favorite:
                    fav_count += 1

            total_items = len(records)

        # Real disk space check
        total_disk, used_disk, free_disk = shutil.disk_usage(self.download_dir)

        return LibraryStats(
            total_items=total_items,
            total_size_bytes=total_size,
            video_count=video_count,
            video_size_bytes=video_size,
            audio_count=audio_count,
            audio_size_bytes=audio_size,
            favorites_count=fav_count,
            categories=categories,
            disk_free_bytes=free_disk,
            disk_total_bytes=total_disk,
            managed_directories=[str(self.download_dir)],
        )

    def _record_to_item(self, r: MediaItemRecord) -> MediaItem:
        tag_list = [t.strip() for t in r.tags.split(",") if t.strip()] if r.tags else []
        return MediaItem(
            id=r.id,
            title=r.title,
            file_path=r.file_path,
            media_type=MediaType(r.media_type),
            format=r.format,
            resolution=r.resolution,
            duration=r.duration,
            file_size=r.file_size,
            thumbnail_path=r.thumbnail_path,
            source_url=r.source_url,
            uploader=r.uploader,
            category=r.category,
            tags=tag_list,
            is_favorite=bool(r.is_favorite),
            collection_name=r.collection_name,
            is_missing=bool(r.is_missing),
            created_at=r.created_at,
            last_accessed=r.last_accessed,
        )


# Global singleton instance
media_library = MediaLibraryManager()
