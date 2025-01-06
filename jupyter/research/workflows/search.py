from typing import Dict, List, Optional
from ..engines import SearchEngine, AnalysisEngine
from .base import ResearchWorkflow
import logging
from datetime import datetime

class SearchWorkflow(ResearchWorkflow):
    def execute(
        self, 
        query: str, 
        analysis_prompt: Optional[str] = None,
        max_results: int = 10
    ) -> Dict:
        try:
            # Run search
            search_results = self.search_engine.search(query, max_results=max_results)
            
            if not search_results:
                return {
                    "status": "error",
                    "message": "No search results found",
                    "timestamp": datetime.now().isoformat()
                }
            
            # If we have an analysis prompt, analyze results
            if analysis_prompt:
                analysis_input = "\n\n".join([
                    f"Title: {r['title']}\nSnippet: {r['snippet']}"
                    for r in search_results
                ])
                analysis = self.analysis_engine.analyze(
                    analysis_input,
                    system_prompt=analysis_prompt
                )
            else:
                analysis = None
            
            return {
                "status": "success",
                "query": query,
                "results": search_results,
                "analysis": analysis,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Search workflow error: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            } 