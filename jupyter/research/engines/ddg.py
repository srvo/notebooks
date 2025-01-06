from typing import List, Dict
from duckduckgo_search import DDGS
from ratelimit import limits, sleep_and_retry
from .base import SearchEngine
import logging

class DuckDuckGoEngine(SearchEngine):
    def __init__(self):
        self.ddgs = DDGS()
        self.calls_per_minute = 15
    
    @sleep_and_retry
    @limits(calls=15, period=60)
    def search(self, query: str, max_results: int = 10, **kwargs) -> List[Dict]:
        results = []
        try:
            search_results = list(self.ddgs.text(
                query,
                region=kwargs.get('region', 'wt-wt'),
                safesearch=kwargs.get('safesearch', 'moderate'),
                max_results=max_results
            ))
            
            logging.info(f"Found {len(search_results)} raw results")
            
            for r in search_results:
                try:
                    link = None
                    if isinstance(r, dict):
                        for field in ['link', 'url', 'href']:
                            link = r.get(field)
                            if link:
                                break
                    
                    results.append({
                        'title': r.get('title', 'No title'),
                        'link': link or 'No link',
                        'snippet': r.get('body', r.get('snippet', 'No snippet')),
                        'source': 'ddg',
                        'raw': r
                    })
                except AttributeError:
                    logging.error(f"Unexpected result format: {r}")
                    continue
                    
            logging.info(f"Processed {len(results)} results successfully")
            return results
        except Exception as e:
            logging.error(f"DDG search error: {str(e)}", exc_info=True)
            return [] 