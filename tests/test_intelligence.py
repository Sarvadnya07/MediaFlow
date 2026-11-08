"""
MediaDock Metadata Intelligence & Chapter Extraction Tests.
Verifies title cleanup, keyword and hashtag extraction, chapter timestamp parsing,
category classification, and optional AI disclosure flags.
"""
import pytest
from app.services.intelligence_service import MediaIntelligenceService, media_intelligence


def test_clean_title_removes_marketing_bracket_fluff():
    raw = "Rick Astley - Never Gonna Give You Up [Official Music Video] (4K Remastered)"
    cleaned = media_intelligence.clean_title(raw)
    assert cleaned == "Rick Astley - Never Gonna Give You Up"


def test_chapter_parsing_from_description():
    desc = """
    In this comprehensive tutorial:
    00:00 Introduction & Overview
    01:45 Setting Up Environment
    05:20 Writing the Core Engine
    12:10 Conclusion & Next Steps
    """
    chapters = media_intelligence.extract_chapters_from_description(desc)
    assert len(chapters) == 4
    assert chapters[0].title == "Introduction & Overview"
    assert chapters[0].start_time == 0.0
    assert chapters[1].title == "Setting Up Environment"
    assert chapters[1].start_time == 105.0  # 1m 45s = 105s
    assert chapters[2].title == "Writing the Core Engine"
    assert chapters[2].start_time == 320.0  # 5m 20s = 320s


def test_tag_extraction_and_categorization():
    title = "Python and Rust Async Programming Tutorial"
    desc = "Learn how to build high performance apps with #python and #rust."
    tags = media_intelligence.extract_tags(title, desc)
    category = media_intelligence.classify_category(title, desc)

    assert "python" in tags
    assert "rust" in tags
    assert category in ("Education", "Technology")


def test_enrich_metadata_structure_and_ai_disclosure():
    res = media_intelligence.enrich_metadata(
        title="Sample Tech Review [HD]",
        description="00:00 Start\n01:00 Review\nA deep look into modern hardware benchmarks.",
        duration=180.0,
        use_external_ai=False,
    )
    assert res.cleaned_title == "Sample Tech Review"
    assert len(res.chapters) == 2
    assert res.ai_enhanced is False
    assert res.ai_provider is None
    assert len(res.suggested_tags) > 0
