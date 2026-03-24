import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import Dict, Any, Optional, List
import hashlib
import json
import time
import socket
import ipaddress
from urllib.parse import urlparse
from pathlib import Path
from config.settings import settings
from langchain_core.tools import tool


class WebScraper:
    # Cache entries older than this are considered stale
    DEFAULT_CACHE_MAX_AGE_HOURS = 24

    def __init__(self, cache_dir: Optional[str] = None, cache_max_age_hours: int = DEFAULT_CACHE_MAX_AGE_HOURS):
        self.timeout = 15
        self.cache_max_age_hours = cache_max_age_hours
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        if cache_dir is None:
            self.cache_dir = Path(settings.data_dir) / "cache" / "scraper"
        else:
            self.cache_dir = Path(cache_dir)

        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _is_safe_url(self, url: str) -> bool:
        """Validate URL to prevent Server-Side Request Forgery (SSRF)."""
        if not url.lower().startswith(('http://', 'https://')):
            return False
            
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname
            if not hostname:
                return False
                
            ip_str = socket.gethostbyname(hostname)
            ip = ipaddress.ip_address(ip_str)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
                return False
                
            return True
        except Exception:
            return False

    def _get_cache_path(self, url: str) -> Path:
        url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
        return self.cache_dir / f"{url_hash}.json"

    def _check_cache(self, url: str) -> Optional[Dict[str, Any]]:
        cache_path = self._get_cache_path(url)
        if not cache_path.exists():
            return None

        # Check TTL
        file_age_hours = (time.time() - cache_path.stat().st_mtime) / 3600
        if file_age_hours > self.cache_max_age_hours:
            cache_path.unlink(missing_ok=True)
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _save_cache(self, url: str, data: Dict[str, Any]):
        cache_path = self._get_cache_path(url)
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to write cache for {url}: {e}")

    @retry(
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def _make_request(self, url: str) -> requests.Response:
        if not self._is_safe_url(url):
            raise requests.exceptions.RequestException(f"Unsafe URL rejected (SSRF prevention): {url}")
            
        # Prevent DoS by capping download size and using a dedicated session.
        session = requests.Session()
        session.max_redirects = 3
        response = session.get(url, headers=self.headers, timeout=self.timeout, stream=True)
        
        # Check Content-Length before downloading if available
        cl = response.headers.get('Content-Length')
        if cl and int(cl) > 10 * 1024 * 1024:  # 10MB limit
            response.close()
            raise requests.exceptions.RequestException("Response payload too large")
            
        content = b""
        for chunk in response.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > 10 * 1024 * 1024:
                response.close()
                raise requests.exceptions.RequestException("Response payload too large")
                
        # Monkey patch the internal content property so .text works as expected
        response._content = content
        
        if response.status_code in [401, 403, 404]:
            return response
        response.raise_for_status()
        return response

    @staticmethod
    def _extract_main_content(soup: BeautifulSoup) -> str:
        """
        Prioritize meaningful content areas over the full page.
        Tries <main>, <article>, [role=main] first. Falls back to <body>.
        """
        # Try semantic content areas first
        for selector in ['main', 'article', '[role="main"]', '.content', '#content']:
            container = soup.select_one(selector)
            if container and len(container.get_text(strip=True)) > 200:
                return container.get_text(separator='\n', strip=True)

        # Fallback: full body after removing noise
        return soup.get_text(separator='\n', strip=True)

    @staticmethod
    def _extract_structured_data(soup: BeautifulSoup) -> List[Dict]:
        """Extract JSON-LD structured data (job postings, courses, articles)."""
        structured = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    structured.extend(data)
                else:
                    structured.append(data)
            except (json.JSONDecodeError, TypeError):
                continue
        return structured

    @staticmethod
    def _extract_links(soup: BeautifulSoup, base_url: str, limit: int = 15) -> List[Dict[str, str]]:
        """Extract the most relevant links from the page."""
        links = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            href_lower = href.strip().lower()
            if not text or len(text) < 3 or href_lower.startswith("#") or href_lower.startswith("javascript:") or href_lower.startswith("data:"):
                continue
            # Resolve relative URLs
            if href.startswith("/"):
                from urllib.parse import urlparse
                parsed = urlparse(base_url)
                href = f"{parsed.scheme}://{parsed.netloc}{href}"
            if href not in seen:
                seen.add(href)
                links.append({"text": text[:100], "url": href})
            if len(links) >= limit:
                break
        return links

    @staticmethod
    def _clean_text(raw_text: str, max_chars: int = 10000) -> str:
        """Clean and truncate text intelligently."""
        lines = (line.strip() for line in raw_text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean = '\n'.join(chunk for chunk in chunks if chunk)
        if len(clean) > max_chars:
            # Truncate at a paragraph boundary if possible
            cutoff = clean[:max_chars].rfind('\n\n')
            if cutoff > max_chars * 0.7:
                clean = clean[:cutoff] + "\n\n[... truncated]"
            else:
                clean = clean[:max_chars] + "\n\n[... truncated]"
        return clean

    def scrape(self, url: str, use_cache: bool = True) -> str:
        """
        Robust scraper with caching, structured data extraction, and smart truncation.
        Returns a JSON string with: content, title, links, structured_data.
        """
        if use_cache:
            cached = self._check_cache(url)
            if cached:
                return json.dumps({"source": "cache", "url": url, **cached})

        try:
            response = self._make_request(url)

            if response.status_code == 403:
                return json.dumps({"error": "Blocked (403 Forbidden). The site has anti-scraping protections. Try using tavily_search instead.", "url": url})
            elif response.status_code == 404:
                return json.dumps({"error": "Page not found (404).", "url": url})
            elif response.status_code != 200:
                return json.dumps({"error": f"HTTP Error {response.status_code}.", "url": url})

            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove noise elements
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]):
                tag.decompose()

            # Extract all data types
            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            main_text = self._extract_main_content(soup)
            clean_text = self._clean_text(main_text)
            structured_data = self._extract_structured_data(soup)
            links = self._extract_links(soup, url)

            data = {
                "title": title,
                "content": clean_text,
                "structured_data": structured_data[:5],  # Limit to 5 entries
                "links": links,
            }

            self._save_cache(url, data)

            return json.dumps({"source": "live", "url": url, **data})

        except requests.exceptions.RequestException as e:
            return json.dumps({
                "error": "Failed to fetch page after multiple retries.",
                "details": str(e),
                "url": url
            })


_scraper_instance = WebScraper()


@tool
def robust_web_scrape(url: str, bypass_cache: bool = False) -> str:
    """
    Scrapes the textual content of a provided URL.
    Uses caching (24h TTL), retry with backoff, and smart content extraction.
    Returns JSON with: title, content (main text), structured_data (JSON-LD), and links.
    For sites that block scraping (LinkedIn, Indeed), use tavily_search instead.

    Args:
        url: The full HTTP/HTTPS URL to scrape.
        bypass_cache: If true, forces a live network request ignoring the local cache.
    """
    return _scraper_instance.scrape(url, use_cache=not bypass_cache)
