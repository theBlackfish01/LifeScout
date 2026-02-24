import os
from pathlib import Path
from tools import SearchTool, WebScraper, DocumentParser, DocumentGenerator, FileManager
from config.settings import settings
import uuid

def run_tests():
    print("Testing Shared Modules...")
    
    # 1. Search Tool
    print("\n--- Testing Tavily Search ---")
    searcher = SearchTool()
    if searcher.api_key:
        res = searcher.search("LangGraph python architecture summary", search_depth="basic")
        print("Tavily Search success. Length:", len(res))
        assert len(res) > 0, "No results returned"
    else:
         print("Skipping Tavily test (no API Key)")

    # 2. Web Scraper
    print("\n--- Testing Web Scraper ---")
    scraper = WebScraper()
    # Test valid scrape
    res = scraper.scrape("https://example.com", use_cache=False)
    assert "source" in res, "Scrape failed"
    print("Live scrape success. Length:", len(res))
    
    # Test cache scrape
    res_cache = scraper.scrape("https://example.com", use_cache=True)
    assert 'cache' in res_cache, "Cache retrieve failed"
    print("Cache scrape success.")
    
    # Test 404 degredation
    res_404 = scraper.scrape("https://example.com/this-page-does-not-exist-1234")
    assert '404' in res_404, "404 degredation failed"
    print("404 Graceful degredation success.")

    # 3. Document Generator
    print("\n--- Testing Document Generator ---")
    gen = DocumentGenerator()
    md_content = "# Test Doc\n\nThis is a *test* document for python-docx and Weasyprint."
    
    pdf_path = Path(settings.data_dir) / "test_gen.pdf"
    docx_path = Path(settings.data_dir) / "test_gen.docx"
    
    res_pdf = gen.generate(md_content, str(pdf_path), "pdf")
    res_docx = gen.generate(md_content, str(docx_path), "docx")
    
    assert pdf_path.exists(), "PDF not generated"
    assert docx_path.exists(), "DOCX not generated"
    print("Generated PDF and DOCX successfully.")

    # 4. Document Parser
    print("\n--- Testing Document Parser ---")
    parser = DocumentParser()
    txt_pdf = parser.parse(str(pdf_path))
    txt_docx = parser.parse(str(docx_path))
    
    assert len(txt_pdf) > 0, "PDF text empty"
    assert len(txt_docx) > 0, "DOCX text empty"
    print(f"Parsed PDF len: {len(txt_pdf)}, DOCX len: {len(txt_docx)}")
    
    # Clean up gen files
    pdf_path.unlink()
    docx_path.unlink()

    # 5. File Manager Context Wrapper
    print("\n--- Testing File Manager IO Wrapper ---")
    fm = FileManager()
    task_id = str(uuid.uuid4())
    save_res = fm.save_agent_artifact("career", task_id, "report", "Test Artifact", "md", "# Hello")
    assert "Error" not in save_res, f"Failed to save artifact: {save_res}"
    print("File Manager Context Save Success.")

    print("\nAll Tool Tests Passed Successfully.")

if __name__ == "__main__":
    run_tests()
