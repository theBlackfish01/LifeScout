import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import Dict, Any, Optional
import hashlib
import json
from pathlib import Path
from config.settings import settings
from langchain_core.tools import tool

class WebScraper:
    def __init__(self, cache_dir: Optional[str] = None):
        self.timeout = 10
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        if cache_dir is None:
            self.cache_dir = Path(settings.data_dir) / "cache" / "scraper"
        else:
            self.cache_dir = Path(cache_dir)
            
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, url: str) -> Path:
        url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
        return self.cache_dir / f"{url_hash}.json"

    def _check_cache(self, url: str) -> Optional[Dict[str, Any]]:
        cache_path = self._get_cache_path(url)
        if cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def _save_cache(self, url: str, data: Dict[str, Any]):
        cache_path = self._get_cache_path(url)
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to write cache for {url}: {e}")

    # Retry on RequestException (Network/DNS) or standard HTTP errors (500s, rate limits) but NOT on 404s
    @retry(
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def _make_request(self, url: str) -> requests.Response:
        response = requests.get(url, headers=self.headers, timeout=self.timeout)
        # We explicitly don't retry on 404, 401, 403 as backoff won't help
        if response.status_code in [401, 403, 404]:
            return response
            
        response.raise_for_status() # This triggers retries for 500s if wrapped in RequestException
        return response

    def scrape(self, url: str, use_cache: bool = True) -> str:
        """
        Robust scraper implementing caching, extraction and safe degredation.
        Returns a JSON formatted string denoting success or structural errors.
        """
        if use_cache:
            cached = self._check_cache(url)
            if cached:
                return json.dumps({"source": "cache", "url": url, "content": cached["content"]})

        try:
            response = self._make_request(url)
            
            if response.status_code == 403:
                result = {"error": "Blocked (403 Forbidden). Anti-scraping mechanism detected.", "url": url}
                return json.dumps(result)
            elif response.status_code == 404:
                result = {"error": "Page not found (404).", "url": url}
                return json.dumps(result)
            elif response.status_code != 200:
                result = {"error": f"HTTP Error {response.status_code}.", "url": url}
                return json.dumps(result)

            # Parse
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove scripts and styles
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()

            # Get text
            text = soup.get_text(separator='\n', strip=True)
            
            # Basic cleanup: remove excessive newlines
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            clean_text = '\n'.join(chunk for chunk in chunks if chunk)

            data = {
                "title": soup.title.string if soup.title else "",
                "content": clean_text[:8000] # LLM token safety constraint
            }

            self._save_cache(url, data)
            
            return json.dumps({
                "source": "live", 
                "url": url, 
                "title": data["title"],
                "content": data["content"]
            })

        except requests.exceptions.RequestException as e:
            # Reached after all tenacity retries fail
            return json.dumps({
                "error": "Failed to fetch page after multiple retries due to network or timeout issues.",
                "details": str(e),
                "url": url
            })

_scraper_instance = WebScraper()

@tool
def robust_web_scrape(url: str, bypass_cache: bool = False) -> str:
    """
    Scrapes the textual content of a provided URL.
    Uses an intelligent caching system and retry mechanism with exponential backoff.
    Removes headers, footers, scripts, and navigation sections to return the core readable content.
    Returns JSON formatted strings indicating success, cache hits, or specific blocking/network errors.
    
    Args:
        url: The full HTTP/HTTPS URL to scrape.
        bypass_cache: If true, forces a live network request ignoring the local cache.
    """
    return _scraper_instance.scrape(url, use_cache=not bypass_cache)
