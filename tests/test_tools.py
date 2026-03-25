"""
Tool module tests.

Unit tests: save_artifact collision prevention, document generation/parsing (no API keys).
Integration tests: Tavily search, live web scraping (require API keys).
"""
import uuid
import pytest
from pathlib import Path

from tools.save_artifact import save_artifact
from config.settings import settings


# ---------------------------------------------------------------------------
# save_artifact (unit, no API key)
# ---------------------------------------------------------------------------

def test_save_artifact_creates_file(tmp_data_dir):
    path = save_artifact("career", "resume", "task_1", "# My Resume\n\nContent here.")
    assert path.exists()
    assert path.read_text(encoding="utf-8") == "# My Resume\n\nContent here."


def test_save_artifact_path_format(tmp_data_dir):
    path = save_artifact("life", "goals", "task_abc", "content")
    assert path.name == "goals_task_abc.md"
    assert "life" in str(path)
    assert "artifacts" in str(path)


def test_save_artifact_collision_prevention(tmp_data_dir):
    """Same group/name/task_id must produce distinct files."""
    path1 = save_artifact("career", "resume", "dup_task", "first version")
    path2 = save_artifact("career", "resume", "dup_task", "second version")
    assert path1 != path2, "Collision: same filename written twice"
    assert path1.exists()
    assert path2.exists()


def test_save_artifact_creates_parent_dirs(tmp_data_dir):
    path = save_artifact("learning", "study_plan", "new_task", "content")
    assert path.parent.is_dir()


# ---------------------------------------------------------------------------
# DocumentGenerator + DocumentParser (unit, no API key — WeasyPrint is mocked)
# ---------------------------------------------------------------------------

def test_document_generator_creates_docx(tmp_data_dir):
    from tools.document_generator import DocumentGenerator
    gen = DocumentGenerator()
    docx_path = tmp_data_dir / "test_gen.docx"
    gen.generate("# Test\n\nContent.", str(docx_path), "docx")
    assert docx_path.exists()
    assert docx_path.stat().st_size > 0


def test_document_parser_reads_docx(tmp_data_dir):
    from tools.document_generator import DocumentGenerator
    from tools.document_parser import DocumentParser
    gen = DocumentGenerator()
    docx_path = tmp_data_dir / "parse_test.docx"
    gen.generate("# Hello World\n\nThis is a test.", str(docx_path), "docx")

    parser = DocumentParser()
    text = parser.parse(str(docx_path))
    assert len(text) > 0


# ---------------------------------------------------------------------------
# Integration: Tavily search (requires TAVILY_API_KEY)
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_tavily_search_returns_results(require_tavily_key):
    from tools import SearchTool
    searcher = SearchTool()
    result = searcher.search("LangGraph python multi-agent framework", search_depth="basic")
    assert len(result) > 0


# ---------------------------------------------------------------------------
# Integration: web scraper (live HTTP, no key needed but marked integration)
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_web_scraper_fetches_example_com():
    from tools import WebScraper
    scraper = WebScraper()
    result = scraper.scrape("https://example.com", use_cache=False)
    assert "source" in result


@pytest.mark.integration
def test_web_scraper_caches_result():
    from tools import WebScraper
    scraper = WebScraper()
    scraper.scrape("https://example.com", use_cache=False)
    cached = scraper.scrape("https://example.com", use_cache=True)
    assert "cache" in cached


@pytest.mark.integration
def test_web_scraper_graceful_404():
    from tools import WebScraper
    scraper = WebScraper()
    result = scraper.scrape("https://example.com/this-page-does-not-exist-99999")
    assert "404" in result or "error" in result.lower()
