from langchain_core.tools import tool
from tavily import TavilyClient
import json
from config.settings import settings

class SearchTool:
    def __init__(self):
        self.api_key = settings.tavily_api_key
        if not self.api_key:
            print("Warning: TAVILY_API_KEY is not set.")
            self.client = None
        else:
            self.client = TavilyClient(api_key=self.api_key)

    def search(self, query: str, search_depth: str = "basic") -> str:
        if not self.client:
            return json.dumps({"error": "Tavily API key not configured."})
        
        try:
            response = self.client.search(
                query=query, 
                search_depth=search_depth,
                include_answer=True
            )
            # Simplify response for LLM Context Windows
            results = []
            if "answer" in response and response["answer"]:
                results.append(f"AI Summary: {response['answer']}")
                
            for res in response.get("results", []):
                results.append(f"Source: {res.get('url')}\nContent: {res.get('content')}")
            
            if not results:
                return "No useful results found."
            
            return "\n\n---\n\n".join(results)
        except Exception as e:
            return json.dumps({"error": str(e)})

_search_instance = SearchTool()

@tool
def tavily_search(query: str, search_depth: str = "basic") -> str:
    """
    Perform a web search using the Tavily API. Useful for finding up-to-date information,
    job listings, educational resources, or specific facts.
    
    Args:
        query: The search query string.
        search_depth: 'basic' or 'advanced'. Advanced is slower but more comprehensive.
    
    Returns:
        Formatted string containing search summaries and source content.
    """
    return _search_instance.search(query, search_depth)


@tool
def search_jobs(query: str, location: str = "") -> str:
    """
    Search for job postings across major job boards.
    Uses advanced search depth and filters for LinkedIn, Indeed, Glassdoor, and similar platforms.
    
    Args:
        query: Job search query (e.g. "senior Python developer").
        location: Geographic filter (e.g. "London, UK" or "remote").
    
    Returns:
        Formatted string with job-relevant search results.
    """
    full_query = f"{query} {location} job posting".strip()
    if not _search_instance.client:
        return json.dumps({"error": "Tavily API key not configured."})
    try:
        response = _search_instance.client.search(
            query=full_query,
            search_depth="advanced",
            include_answer=True,
            include_domains=["linkedin.com/jobs", "indeed.com", "glassdoor.com", "wellfound.com", "remoteok.com"],
        )
        results = []
        if response.get("answer"):
            results.append(f"AI Summary: {response['answer']}")
        for res in response.get("results", []):
            results.append(f"Source: {res.get('url')}\nTitle: {res.get('title', '')}\nContent: {res.get('content')}")
        return "\n\n---\n\n".join(results) if results else "No job postings found."
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def search_courses(query: str) -> str:
    """
    Search for online courses and educational resources.
    Filters for Coursera, Udemy, edX, Pluralsight, and similar platforms.
    
    Args:
        query: Course topic (e.g. "machine learning beginner").
    
    Returns:
        Formatted string with course-relevant search results.
    """
    full_query = f"{query} online course"
    if not _search_instance.client:
        return json.dumps({"error": "Tavily API key not configured."})
    try:
        response = _search_instance.client.search(
            query=full_query,
            search_depth="advanced",
            include_answer=True,
            include_domains=["coursera.org", "udemy.com", "edx.org", "pluralsight.com", "linkedin.com/learning"],
        )
        results = []
        if response.get("answer"):
            results.append(f"AI Summary: {response['answer']}")
        for res in response.get("results", []):
            results.append(f"Source: {res.get('url')}\nTitle: {res.get('title', '')}\nContent: {res.get('content')}")
        return "\n\n---\n\n".join(results) if results else "No courses found."
    except Exception as e:
        return json.dumps({"error": str(e)})

