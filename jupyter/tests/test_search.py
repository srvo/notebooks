import unittest
from unittest.mock import Mock, patch
from ..research.engines import SearchEngine, AnalysisEngine
from ..research.workflows.search import SearchWorkflow

class TestSearchWorkflow(unittest.TestCase):
    def setUp(self):
        self.mock_search = Mock(spec=SearchEngine)
        self.mock_analysis = Mock(spec=AnalysisEngine)
        self.workflow = SearchWorkflow(
            search_engine=self.mock_search,
            analysis_engine=self.mock_analysis
        )
    
    def test_basic_search(self):
        # Mock search results
        mock_results = [
            {
                'title': 'Test Result',
                'link': 'https://test.com',
                'snippet': 'Test snippet',
                'source': 'ddg'
            }
        ]
        self.mock_search.search.return_value = mock_results
        
        # Run workflow
        result = self.workflow.execute("test query")
        
        # Verify
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['query'], 'test query')
        self.assertEqual(result['results'], mock_results)
        self.assertIsNone(result['analysis'])
        
        # Verify search was called correctly
        self.mock_search.search.assert_called_once_with(
            "test query", 
            max_results=10
        )
    
    def test_search_with_analysis(self):
        # Mock search and analysis results
        mock_results = [
            {
                'title': 'Test Result',
                'link': 'https://test.com',
                'snippet': 'Test snippet',
                'source': 'ddg'
            }
        ]
        mock_analysis = {"analysis": "test analysis"}
        
        self.mock_search.search.return_value = mock_results
        self.mock_analysis.analyze.return_value = mock_analysis
        
        # Run workflow
        result = self.workflow.execute(
            "test query",
            analysis_prompt="Analyze these results"
        )
        
        # Verify
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['analysis'], mock_analysis)
        
        # Verify both engines were called
        self.mock_search.search.assert_called_once()
        self.mock_analysis.analyze.assert_called_once()

if __name__ == '__main__':
    unittest.main() 