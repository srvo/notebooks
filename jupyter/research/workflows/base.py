from typing import Dict, List
from ..engines import SearchEngine, AnalysisEngine

class ResearchWorkflow:
    def __init__(
        self, 
        search_engine: SearchEngine,
        analysis_engine: AnalysisEngine
    ):
        self.search_engine = search_engine
        self.analysis_engine = analysis_engine
    
    def execute(self, **kwargs):
        raise NotImplementedError 