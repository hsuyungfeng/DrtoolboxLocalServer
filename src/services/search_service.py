import logging
from duckduckgo_search import DDGS
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class WebSearchService:
    def __init__(self):
        self.ddgs = DDGS()

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Performs a web search and returns results."""
        logger.info(f"Performing web search for: {query}")
        try:
            results = self.ddgs.text(query, max_results=max_results)
            return [
                {
                    "title": r.get('title'),
                    "body": r.get('body'),
                    "href": r.get('href')
                } for r in results
            ]
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []

search_service = WebSearchService()
