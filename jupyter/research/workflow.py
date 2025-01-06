from typing import Dict
import logging

class SearchWorkflow:
    def __init__(self, search_engine, analysis_engine):
        self.search_engine = search_engine
        self.analysis_engine = analysis_engine
        self.logger = logging.getLogger(__name__)
    
    def run(self, query: str) -> Dict:
        # Run search
        self.logger.info(f"Running search for query: {query}")
        results = self.search_engine.search(query)
        
        # Run analysis
        self.logger.info("Running analysis on search results")
        analysis = self.analysis_engine.analyze(results)
        
        return {
            "query": query,
            "results": results,
            "analysis": analysis,
        } 