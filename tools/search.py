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
