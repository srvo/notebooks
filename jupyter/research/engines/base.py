import logging
from typing import Optional, List, Dict
from research.llm import LLMClient

class BaseEngine:
    """Base class for all research engines
    
    Provides common functionality like:
    - Logging setup
    - LLM client initialization
    - Basic configuration
    """
    
    def __init__(self):
        # Set up logging
        self.logger = logging.getLogger(self.__class__.__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # Initialize LLM client
        self.llm = LLMClient()
    
    async def process(self):
        """Main processing method to be implemented by subclasses"""
        raise NotImplementedError

class SearchEngine:
    """Base class for search engines"""
    def search(self, query: str, max_results: int = 10, **kwargs) -> List[Dict]:
        raise NotImplementedError("Subclasses must implement search method")

class AnalysisEngine:
    """Base class for analysis engines"""
    def analyze(self, results: List[Dict]) -> Dict:
        raise NotImplementedError("Subclasses must implement analyze method") 