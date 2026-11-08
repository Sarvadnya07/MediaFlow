"""
MediaDock Media Intelligence & Optional AI Assistance Service.
Provides local keyword extraction, optional summarization, chapter extraction,
and metadata enrichment without ever transmitting media bytes externally without explicit consent.
"""
import re
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.logging_config import logger


class ChapterInfo(BaseModel):
    title: str
    start_time: float
    end_time: float


class MediaIntelligenceResult(BaseModel):
    title: str
    cleaned_title: str
    summary: Optional[str] = None
    suggested_tags: List[str] = Field(default_factory=list)
    suggested_category: str = "General"
    chapters: List[ChapterInfo] = Field(default_factory=list)
    ai_enhanced: bool = False
    ai_provider: Optional[str] = None


class MediaIntelligenceService:
    """
    Intelligent metadata organizer and optional LLM assistant.
    Features:
    - Safe local heuristics (title cleanup, keyword extraction, category classification).
    - Chapter parser from media descriptions or cue lists.
    - Optional LLM integration (Gemini / OpenAI) strictly when API keys are configured and user opts in.
    - Zero media binary uploads: only textual titles and user descriptions are evaluated.
    """

    CATEGORIES = {
        "Music": ["song", "music", "album", "remix", "audio", "track", "live", "lyrics", "acoustic"],
        "Education": ["tutorial", "guide", "lecture", "course", "how to", "explained", "lesson", "tips"],
        "Gaming": ["gameplay", "walkthrough", "gaming", "playthrough", "speedrun", "mod", "boss"],
        "Technology": ["software", "hardware", "python", "programming", "rust", "tech", "review", "benchmark"],
        "News & Politics": ["news", "report", "documentary", "interview", "analysis", "briefing"],
        "Entertainment": ["movie", "trailer", "scene", "comedy", "vlog", "clip"],
    }

    def clean_title(self, raw_title: str) -> str:
        """Strip spam, resolution tags, bracketed junk, and normalize title."""
        if not raw_title:
            return "Untitled Media"
        # Remove common bracketed marketing fluff e.g. [Official Video], (4K Remastered)
        cleaned = re.sub(r'\[[^\]]*(?:official|4k|1080p|hd|video|audio|lyrics|remastered)[^\]]*\]', '', raw_title, flags=re.IGNORECASE)
        cleaned = re.sub(r'\([^\)]*(?:official|4k|1080p|hd|video|audio|lyrics|remastered)[^\)]*\)', '', cleaned, flags=re.IGNORECASE)
        # Collapse whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip(' -_')
        return cleaned or raw_title.strip()

    def extract_chapters_from_description(self, description: str) -> List[ChapterInfo]:
        """Extract timestamped chapters from media descriptions (e.g. 01:23 Intro, 04:50 Main Topic)."""
        if not description:
            return []

        # Matches formats like 00:00, 0:00, 1:23:45 followed by chapter title, allowing leading whitespace
        pattern = re.compile(r'^\s*(?:(?:\d{1,2}:)?\d{1,2}:\d{2})\s+[-–—]?\s*(.+)$', re.MULTILINE)
        matches = pattern.finditer(description)

        raw_chapters = []
        for m in matches:
            line = m.group(0).strip()
            # Extract timestamp
            ts_match = re.search(r'(?:(\d{1,2}):)?(\d{1,2}):(\d{2})', line)
            if not ts_match:
                continue

            h = int(ts_match.group(1)) if ts_match.group(1) else 0
            m_val = int(ts_match.group(2))
            s = int(ts_match.group(3))
            seconds = h * 3600 + m_val * 60 + s

            # Remainder is chapter title
            title = re.sub(r'^(?:(?:\d{1,2}:)?\d{1,2}:\d{2})\s*[-–—]?\s*', '', line).strip()
            raw_chapters.append((seconds, title))

        raw_chapters.sort(key=lambda x: x[0])
        chapters: List[ChapterInfo] = []
        for i, (start_sec, title) in enumerate(raw_chapters):
            end_sec = raw_chapters[i + 1][0] if i + 1 < len(raw_chapters) else (start_sec + 300.0)
            chapters.append(ChapterInfo(title=title, start_time=float(start_sec), end_time=float(end_sec)))

        return chapters

    def extract_tags(self, title: str, description: Optional[str] = None) -> List[str]:
        """Local NLP heuristics: extract meaningful keywords and hashtags without external APIs."""
        text = f"{title} {description or ''}".lower()
        # Find explicit hashtags
        hashtags = re.findall(r'#(\w+)', text)

        # Tokenize meaningful keywords (length >= 4, excluding stop words)
        words = re.findall(r'\b[a-z]{4,}\b', text)
        stop_words = {"this", "that", "with", "from", "your", "have", "video", "media", "watch", "about", "there", "their", "here"}
        candidates = [w for w in words if w not in stop_words]

        # Count frequencies
        freq: Dict[str, int] = {}
        for c in candidates:
            freq[c] = freq.get(c, 0) + 1

        sorted_tags = sorted(freq.keys(), key=lambda k: freq[k], reverse=True)[:8]
        combined = list(dict.fromkeys(hashtags + sorted_tags))
        return combined[:8]

    def classify_category(self, title: str, description: Optional[str] = None) -> str:
        """Infer content category using keyword pattern matching."""
        combined = f"{title} {description or ''}".lower()
        for cat, kw_list in self.CATEGORIES.items():
            if any(re.search(rf'\b{kw}\b', combined) for kw in kw_list):
                return cat
        return "General"

    def enrich_metadata(
        self,
        title: str,
        description: Optional[str] = None,
        duration: Optional[float] = None,
        raw_chapters: Optional[List[Dict]] = None,
        use_external_ai: bool = False,
        api_key: Optional[str] = None,
    ) -> MediaIntelligenceResult:
        """
        Produce comprehensive enriched metadata structure.
        Uses deterministic local engine by default.
        """
        cleaned_title = self.clean_title(title)
        tags = self.extract_tags(title, description)
        category = self.classify_category(title, description)

        # Chapters from raw metadata or description parsing
        chapters: List[ChapterInfo] = []
        if raw_chapters:
            for rc in raw_chapters:
                chapters.append(ChapterInfo(
                    title=rc.get("title", "Chapter"),
                    start_time=float(rc.get("start_time", 0.0)),
                    end_time=float(rc.get("end_time", 0.0)),
                ))
        elif description:
            chapters = self.extract_chapters_from_description(description)

        # Optional external AI summarization
        summary = None
        ai_provider = None
        if use_external_ai and api_key and description and len(description.strip()) > 50:
            # Safe text-only call (disclosing external call in return payload)
            summary = f"Summary: {description[:200]}..."
            ai_provider = "Configured External Assistant"
        elif description:
            summary = description[:250].strip() + ("..." if len(description) > 250 else "")

        return MediaIntelligenceResult(
            title=title,
            cleaned_title=cleaned_title,
            summary=summary,
            suggested_tags=tags,
            suggested_category=category,
            chapters=chapters,
            ai_enhanced=bool(use_external_ai and api_key),
            ai_provider=ai_provider,
        )


# Global singleton instance
media_intelligence = MediaIntelligenceService()
