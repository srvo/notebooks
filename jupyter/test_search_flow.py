import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import os
from concurrent.futures import ThreadPoolExecutor
import requests

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from search_flow import (
    is_investment_product,
    get_top_companies,
    generate_summary,
    extract_structured_data,
    Source,
    get_company_context,
    generate_search_queries,
    ResearchWorkflow,
    call_deepseek_api,
    RateLimitedDDGS,
    CHECKPOINT_STAGES,
    get_connection,
    get_research_status,
    get_incomplete_research
)

class TestInvestmentProductClassification(unittest.TestCase):
    def test_clear_investment_product(self):
        """Test obvious investment product identification"""
        result = is_investment_product(
            "BlackRock ESG ETF Trust",
            "ETFX",
            "An exchange-traded fund"
        )
        self.assertTrue(result['is_investment_product'])
        self.assertGreaterEqual(result['confidence'], 75)

    def test_clear_operating_company(self):
        """Test obvious operating company identification"""
        result = is_investment_product(
            "Apple Inc",
            "AAPL",
            "Technology company"
        )
        self.assertFalse(result['is_investment_product'])
        self.assertLess(result['confidence'], 50)

    def test_preferred_share_detection(self):
        """Test preferred share detection"""
        result = is_investment_product(
            "Company Name Preferred Series A",
            "CPRA",
            None
        )
        self.assertTrue(result['is_investment_product'])
        self.assertIn("PR[A-Z]", str(result['matches']))

class TestSourceClass(unittest.TestCase):
    def test_source_initialization(self):
        """Test Source class initialization and hash generation"""
        source = Source(
            url="https://example.com/article",
            title="Test Article",
            snippet="Test snippet",
            domain="",
            source_type="web",
            category="environmental_safety",
            query_context="test query",
            retrieved_at=datetime.now(timezone.utc).isoformat()
        )
        self.assertEqual(source.domain, "example.com")
        self.assertIsNotNone(source.source_hash)

    def test_source_deduplication(self):
        """Test that identical sources generate the same hash"""
        source1 = Source(
            url="https://example.com/article",
            title="Test Article",
            snippet="Test snippet",
            domain="",
            source_type="web",
            category="environmental_safety",
            query_context="test query",
            retrieved_at=datetime.now(timezone.utc).isoformat()
        )
        source2 = Source(
            url="https://example.com/article",
            title="Test Article",
            snippet="Test snippet",
            domain="",
            source_type="web",
            category="environmental_safety",
            query_context="different query",
            retrieved_at=datetime.now(timezone.utc).isoformat()
        )
        self.assertEqual(source1.source_hash, source2.source_hash)

class TestDeepSeekAPI(unittest.TestCase):
    @patch('requests.post')
    def test_api_call_success(self, mock_post):
        """Test successful API call"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "test"}}]}
        mock_post.return_value = mock_response

        messages = [{"role": "user", "content": "test"}]
        result = call_deepseek_api(messages)
        self.assertIsNotNone(result)
        self.assertEqual(result["choices"][0]["message"]["content"], "test")

    @patch('requests.post')
    def test_api_call_failure(self, mock_post):
        """Test API call failure"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        messages = [{"role": "user", "content": "test"}]
        result = call_deepseek_api(messages)
        self.assertIsNone(result)

class TestSearchUtilities(unittest.TestCase):
    def setUp(self):
        self.ddgs = RateLimitedDDGS(timeout=5)

    @patch('duckduckgo_search.DDGS.text')
    def test_web_search(self, mock_text):
        """Test web search functionality"""
        mock_text.return_value = [
            {"title": "Test", "link": "https://example.com", "body": "Test body"}
        ]
        results = self.ddgs.search("test query")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Test")

    @patch('duckduckgo_search.DDGS.news')
    def test_news_search(self, mock_news):
        """Test news search functionality"""
        mock_news.return_value = [
            {"title": "Test", "link": "https://example.com", "body": "Test body"}
        ]
        results = self.ddgs.news_search("test query")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Test")

class TestResearchWorkflow(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        # Create necessary tables
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Create research_checkpoints table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS research_checkpoints (
                    company_ticker TEXT PRIMARY KEY,
                    stage INTEGER NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    partial_results JSON,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0
                )
            """)
            
            # Create research_sources table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS research_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_ticker TEXT NOT NULL,
                    source_hash TEXT NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT,
                    snippet TEXT,
                    domain TEXT,
                    source_type TEXT,
                    category TEXT,
                    query_context TEXT,
                    retrieved_at TIMESTAMP,
                    published_date TEXT,
                    UNIQUE(company_ticker, source_hash),
                    FOREIGN KEY (company_ticker) REFERENCES companies (ticker)
                )
            """)
            
            # Create research_results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS research_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_ticker TEXT NOT NULL UNIQUE,
                    company_context TEXT,
                    summary TEXT,
                    risk_score INTEGER,
                    recommendation TEXT,
                    confidence_score INTEGER,
                    structured_data JSON,
                    raw_results JSON,
                    search_queries JSON,
                    metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_ticker) REFERENCES companies (ticker)
                )
            """)
            
            # Create companies table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    ticker TEXT NOT NULL UNIQUE,
                    isin TEXT,
                    tick INTEGER,
                    industry TEXT,
                    category TEXT,
                    sector TEXT,
                    description TEXT,
                    last_tick_date TEXT,
                    workflow TEXT,
                    excluded BOOLEAN DEFAULT FALSE,
                    note TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def tearDown(self):
        """Clean up test environment"""
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if tables exist before trying to delete from them
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('research_checkpoints', 'research_sources', 'research_results', 'companies')
            """)
            existing_tables = {row[0] for row in cursor.fetchall()}
            
            if 'research_checkpoints' in existing_tables:
                cursor.execute("DELETE FROM research_checkpoints WHERE company_ticker LIKE 'TEST%'")
            if 'research_sources' in existing_tables:
                cursor.execute("DELETE FROM research_sources WHERE company_ticker LIKE 'TEST%'")
            if 'research_results' in existing_tables:
                cursor.execute("DELETE FROM research_results WHERE company_ticker LIKE 'TEST%'")
            if 'companies' in existing_tables:
                cursor.execute("DELETE FROM companies WHERE ticker LIKE 'TEST%'")
            
            conn.commit()

    def setUp(self):
        self.workflow = ResearchWorkflow(timeout=5)

    @patch('search_flow.call_deepseek_api')
    def test_company_context_generation(self, mock_api):
        """Test company context generation"""
        mock_api.return_value = {"choices": [{"message": {"content": "test context"}}]}
        context = get_company_context("Test Company", "TEST")
        self.assertEqual(context, "test context")

    @patch('search_flow.call_deepseek_api')
    def test_search_query_generation(self, mock_api):
        """Test search query generation"""
        mock_queries = [
            {
                "category": "environmental_safety",
                "query": "test query",
                "rationale": "test rationale",
                "priority": 1
            }
        ]
        mock_api.return_value = {"choices": [{"message": {"content": json.dumps(mock_queries)}}]}
        queries = generate_search_queries("Test Company", "test context")
        self.assertEqual(len(queries), 1)
        self.assertEqual(queries[0]["category"], "environmental_safety")

    @patch('search_flow.ResearchWorkflow.execute_search')
    @patch('search_flow.ResearchWorkflow.execute_news_search')
    def test_research_execution(self, mock_news_search, mock_web_search):
        """Test full research execution"""
        # Create a timestamp for consistency
        current_time = datetime.now(timezone.utc).isoformat()
        
        mock_web_search.return_value = [
            {
                "title": "Test",
                "url": "https://example.com",
                "source_hash": "123",
                "link": "https://example.com",
                "source_type": "web",
                "snippet": "Test snippet",
                "domain": "example.com",
                "query_context": "test query",
                "category": "environmental_safety",
                "retrieved_at": current_time,
                "published_date": None  # Web results don't have published dates
            }
        ]
        mock_news_search.return_value = [
            {
                "title": "Test News",
                "url": "https://example.com",
                "source_hash": "456",
                "link": "https://example.com",
                "source_type": "news",
                "snippet": "Test news snippet",
                "domain": "example.com",
                "query_context": "test query",
                "category": "environmental_safety",
                "retrieved_at": current_time,
                "published_date": "2024-01-06"
            }
        ]
        
        test_company = {
            "name": "Test Company",
            "ticker": "TEST",
            "tick": 50
        }
        
        with patch('search_flow.get_company_context') as mock_context, \
             patch('search_flow.generate_search_queries') as mock_queries, \
             patch('search_flow.generate_summary') as mock_summary, \
             patch('search_flow.extract_structured_data') as mock_data, \
             patch('search_flow.get_connection') as mock_db, \
             patch('search_flow.logging') as mock_logging:
            
            # Mock database cursor and operations
            mock_cursor = MagicMock()
            mock_db.return_value.__enter__.return_value.cursor.return_value = mock_cursor
            
            # Track SQL queries and errors for debugging
            executed_queries = []
            errors = []
            
            # Mock checkpoint query response with side effects for different queries
            def mock_fetchone_side_effect(*args, **kwargs):
                # Get the most recent execute call's arguments
                last_execute = mock_cursor.execute.call_args
                if not last_execute:
                    return None
                
                sql = last_execute[0][0].lower()
                executed_queries.append(f"SQL Query: {sql}")
                
                if 'research_checkpoints' in sql and 'select' in sql:
                    return (CHECKPOINT_STAGES['CONTEXT'], json.dumps({'company_context': 'test context'}), 0)
                elif 'select' in sql:
                    return (1,)  # Default for other SELECT queries
                return None
            
            mock_cursor.fetchone.side_effect = mock_fetchone_side_effect
            mock_cursor.fetchall.return_value = []
            
            mock_context.return_value = "test context"
            mock_queries.return_value = [{
                "category": "environmental_safety",
                "query": "test query",
                "rationale": "test rationale",
                "priority": 1
            }]
            mock_summary.return_value = "test summary"
            mock_data.return_value = {
                "risk_score": 50,
                "recommendation": "clear",
                "confidence_score": 75,
                "key_risks": [],
                "controversies": [],
                "environmental_issues": [],
                "social_issues": [],
                "governance_issues": []
            }
            
            # Mock database table creation and operations
            def mock_execute_side_effect(sql, *args, **kwargs):
                try:
                    executed_queries.append(f"Execute SQL: {sql}")
                    print(f"Debug: Executing SQL: {sql}")
                    if args:
                        print(f"Debug: Args: {args}")
                    
                    if 'create table' in sql.lower():
                        return None
                    elif 'insert' in sql.lower():
                        # For insert operations, check if we're updating a checkpoint
                        if 'research_checkpoints' in sql.lower():
                            # Extract the stage value from args
                            if args and len(args[0]) >= 2:
                                stage = args[0][1]
                                if stage is None:
                                    stage = CHECKPOINT_STAGES['CONTEXT']  # Default to CONTEXT stage
                                print(f"Debug: Setting checkpoint stage to {stage}")
                        return None
                    elif 'select' in sql.lower():
                        return None
                    return None
                except Exception as e:
                    errors.append(str(e))
                    print(f"Debug: Error executing SQL: {str(e)}")
                    return None
            
            mock_cursor.execute.side_effect = mock_execute_side_effect
            
            # Ensure tables exist
            workflow = ResearchWorkflow()
            workflow._ensure_checkpoint_table()
            
            # Run the test
            result = workflow.research_company(test_company)
            
            # Print debug information
            print("\nExecuted SQL Queries:")
            for query in executed_queries:
                print(f"Debug: {query}")
            
            if errors:
                print("\nErrors encountered:")
                for error in errors:
                    print(f"Debug: Error: {error}")
            
            if result is None:
                print("\nDebug: All mock calls:")
                print("mock_context calls:", mock_context.mock_calls)
                print("mock_queries calls:", mock_queries.mock_calls)
                print("mock_summary calls:", mock_summary.mock_calls)
                print("mock_data calls:", mock_data.mock_calls)
            
            self.assertIsNotNone(result, "Result should not be None")
            self.assertEqual(result["company"]["ticker"], "TEST")
            self.assertIn("research_results", result)
            self.assertIn("structured_data", result)
            
            # Verify database operations were attempted
            mock_cursor.execute.assert_called()

class TestDatabaseOperations(unittest.TestCase):
    def setUp(self):
        # Create a temporary database for testing
        self.test_db_path = Path("test_research.db")
        
    def tearDown(self):
        # Clean up the test database
        if self.test_db_path.exists():
            self.test_db_path.unlink()

    @patch('search_flow.get_connection')
    def test_get_top_companies(self, mock_conn):
        """Test getting top companies from database"""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Test Company", "TEST", 50, "Description")
        ]
        mock_conn.return_value.__enter__.return_value.cursor.return_value = mock_cursor
        
        companies = get_top_companies(limit=1)
        self.assertEqual(len(companies), 1)
        self.assertEqual(companies[0]["ticker"], "TEST")

class TestEdgeCases(unittest.TestCase):
    def test_empty_company_name(self):
        """Test handling of empty company name"""
        result = is_investment_product("", "TEST", None)
        self.assertFalse(result['is_investment_product'])
        self.assertEqual(result['confidence'], 0)

    def test_malformed_ticker(self):
        """Test handling of malformed ticker"""
        result = is_investment_product("Test Company", "", None)
        self.assertFalse(result['is_investment_product'])
        self.assertEqual(result['confidence'], 0)

    def test_invalid_url_source(self):
        """Test handling of invalid URL in Source"""
        source = Source(
            url="not_a_url",
            title="Test",
            snippet="Test",
            domain="",
            source_type="web",
            category="environmental_safety",
            query_context="test",
            retrieved_at=datetime.now(timezone.utc).isoformat()
        )
        self.assertEqual(source.domain, "")  # Should handle invalid URL gracefully

class TestRateLimiting(unittest.TestCase):
    def setUp(self):
        self.ddgs = RateLimitedDDGS(timeout=1)

    def test_rate_limit_delay(self):
        """Test that rate limiting adds appropriate delay"""
        start_time = datetime.now()
        self.ddgs._wait_for_rate_limit()
        self.ddgs._wait_for_rate_limit()
        end_time = datetime.now()
        delay = (end_time - start_time).total_seconds()
        self.assertGreaterEqual(delay, 2)  # Should have waited at least DELAY_BETWEEN_SEARCHES seconds

class TestErrorHandling(unittest.TestCase):
    @patch('search_flow.call_deepseek_api')
    def test_api_timeout(self, mock_api):
        """Test handling of API timeout"""
        mock_api.side_effect = Exception("Timeout")  # Simpler timeout simulation
        context = get_company_context("Test Company", "TEST")
        self.assertEqual(context, "Error generating company context")

    @patch('search_flow.call_deepseek_api')
    def test_malformed_api_response(self, mock_api):
        """Test handling of malformed API response"""
        mock_api.return_value = {}  # Empty response
        queries = generate_search_queries("Test Company", "context")
        self.assertEqual(queries, [])

    def test_invalid_json_structured_data(self):
        """Test handling of invalid JSON in structured data extraction"""
        with patch('search_flow.call_deepseek_api') as mock_api:
            mock_api.return_value = {"choices": [{"message": {"content": "invalid json"}}]}
            data = extract_structured_data({}, "summary", "Test Company")
            self.assertEqual(data, {})

class TestDataValidation(unittest.TestCase):
    def test_source_required_fields(self):
        """Test that Source requires all necessary fields"""
        with self.assertRaises(TypeError):
            Source()  # Should raise error when missing required fields

    def test_valid_search_categories(self):
        """Test that search categories are valid"""
        with patch('search_flow.call_deepseek_api') as mock_api:
            # Mock API responses for each category
            mock_api.return_value = {
                "choices": [
                    {
                        "message": {
                            "content": "Test search strategy content"
                        }
                    }
                ]
            }
            
            workflow = ResearchWorkflow()
            prompts = workflow.generate_search_prompts("Test Company")
            
            valid_categories = {"environmental_safety", "financial_legal", "ethical_social"}
            self.assertEqual(len(prompts), len(valid_categories))
            for prompt in prompts:
                self.assertIn(prompt['type'], valid_categories)
                self.assertIsInstance(prompt['content'], str)
                self.assertTrue(prompt['content'])  # Content should not be empty

    def test_priority_range(self):
        """Test that priorities are within valid range"""
        with patch('search_flow.call_deepseek_api') as mock_api:
            # Test with valid priorities
            mock_queries = [
                {
                    "category": "environmental_safety",
                    "query": "test query",
                    "rationale": "test rationale",
                    "priority": 2
                }
            ]
            mock_api.return_value = {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(mock_queries)
                        }
                    }
                ]
            }
            
            queries = generate_search_queries("Test Company", "context")
            self.assertTrue(all(1 <= q.get('priority', 0) <= 3 for q in queries))

            # Test with missing priority
            mock_queries = [
                {
                    "category": "environmental_safety",
                    "query": "test query",
                    "rationale": "test rationale"
                }
            ]
            mock_api.return_value = {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(mock_queries)
                        }
                    }
                ]
            }
            
            queries = generate_search_queries("Test Company", "context")
            self.assertTrue(all(1 <= q.get('priority', 0) <= 3 for q in queries))

    def test_search_prompt_generation(self):
        """Test that search prompts are generated with correct structure"""
        with patch('search_flow.call_deepseek_api') as mock_api:
            mock_api.return_value = {
                "choices": [
                    {
                        "message": {
                            "content": "Generated search strategy with keywords and considerations"
                        }
                    }
                ]
            }
            
            workflow = ResearchWorkflow()
            prompts = workflow.generate_search_prompts("Test Company")
            
            # Should generate prompts for all three categories
            self.assertEqual(len(prompts), 3)
            
            # Each prompt should have the correct structure
            for prompt in prompts:
                self.assertIn('type', prompt)
                self.assertIn('content', prompt)
                self.assertIsInstance(prompt['content'], str)
                self.assertTrue(len(prompt['content']) > 0)
            
            # Mock API should be called exactly three times (one for each category)
            self.assertEqual(mock_api.call_count, 3)

class TestPerformance(unittest.TestCase):
    @patch('search_flow.call_deepseek_api')
    def test_batch_processing_time(self, mock_api):
        """Test performance of batch processing"""
        mock_api.return_value = {"choices": [{"message": {"content": "test"}}]}
        
        start_time = datetime.now()
        workflow = ResearchWorkflow()
        
        # Process 5 companies in parallel
        companies = [{"name": f"Company{i}", "ticker": f"TEST{i}", "tick": 50} for i in range(5)]
        with ThreadPoolExecutor(max_workers=3) as executor:
            list(executor.map(workflow.research_company, companies))
        
        duration = (datetime.now() - start_time).total_seconds()
        self.assertLess(duration, 30)  # Should complete within reasonable time

    def test_source_deduplication_performance(self):
        """Test performance of source deduplication"""
        # Generate 1000 similar sources
        sources = []
        for i in range(1000):
            source = Source(
                url=f"https://example.com/article{i%10}",  # Only 10 unique URLs
                title="Test Article",
                snippet="Test snippet",
                domain="",
                source_type="web",
                category="environmental_safety",
                query_context="test query",
                retrieved_at=datetime.now(timezone.utc).isoformat()
            )
            sources.append(source.__dict__)
        
        start_time = datetime.now()
        unique_sources = {
            source['source_hash']: source 
            for source in sources
        }.values()
        duration = (datetime.now() - start_time).total_seconds()
        
        self.assertLess(duration, 1)  # Deduplication should be fast
        self.assertEqual(len(list(unique_sources)), 10)  # Should find 10 unique sources

class TestCheckpointing(unittest.TestCase):
    def setUp(self):
        """Set up test environment with a clean database"""
        self.workflow = ResearchWorkflow(timeout=5)
        self.test_company = {
            "name": "Test Company",
            "ticker": "TEST",
            "tick": 50,
            "description": "A test company"
        }
        
        # Clean up any existing checkpoints
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM research_checkpoints WHERE company_ticker = ?", 
                         (self.test_company['ticker'],))
            conn.commit()
    
    def test_checkpoint_creation(self):
        """Test that checkpoints are created correctly"""
        self.workflow._update_checkpoint(
            self.test_company['ticker'],
            CHECKPOINT_STAGES['CONTEXT'],
            {'company_context': 'test context'}
        )
        
        checkpoint = self.workflow._get_checkpoint(self.test_company['ticker'])
        self.assertIsNotNone(checkpoint)
        self.assertEqual(checkpoint['stage'], CHECKPOINT_STAGES['CONTEXT'])
        self.assertEqual(checkpoint['partial_results']['company_context'], 'test context')
        self.assertEqual(checkpoint['retry_count'], 0)
    
    def test_checkpoint_retry_count(self):
        """Test that retry count increments correctly"""
        # First attempt
        self.workflow._update_checkpoint(
            self.test_company['ticker'],
            CHECKPOINT_STAGES['CONTEXT'],
            {'company_context': 'test context'}
        )
        
        # Simulate failure and retry
        self.workflow._update_checkpoint(
            self.test_company['ticker'],
            CHECKPOINT_STAGES['CONTEXT'],
            {'company_context': 'test context'},
            error="Test error"
        )
        
        checkpoint = self.workflow._get_checkpoint(self.test_company['ticker'])
        self.assertEqual(checkpoint['retry_count'], 1)
    
    def test_checkpoint_progress(self):
        """Test that checkpoint progress is tracked correctly"""
        stages = [
            (CHECKPOINT_STAGES['CONTEXT'], {'company_context': 'test context'}),
            (CHECKPOINT_STAGES['QUERIES'], {'company_context': 'test context', 'queries': ['test query']}),
            (CHECKPOINT_STAGES['SEARCH'], {'company_context': 'test context', 'queries': ['test query'], 'results': []})
        ]
        
        for stage, partial_results in stages:
            self.workflow._update_checkpoint(self.test_company['ticker'], stage, partial_results)
            checkpoint = self.workflow._get_checkpoint(self.test_company['ticker'])
            self.assertEqual(checkpoint['stage'], stage)
            for key in partial_results:
                self.assertEqual(checkpoint['partial_results'][key], partial_results[key])
    
    @patch('search_flow.get_company_context')
    def test_resume_from_checkpoint(self, mock_context):
        """Test that research can resume from a checkpoint"""
        # Set up mock responses
        mock_context.return_value = "test context"
        
        # Create a checkpoint at CONTEXT stage
        self.workflow._update_checkpoint(
            self.test_company['ticker'],
            CHECKPOINT_STAGES['CONTEXT'],
            {'company_context': 'test context'}
        )
        
        # Run research
        with patch('search_flow.generate_search_queries') as mock_queries, \
             patch('search_flow.ResearchWorkflow.execute_search') as mock_search, \
             patch('search_flow.ResearchWorkflow.execute_news_search') as mock_news, \
             patch('search_flow.generate_summary') as mock_summary, \
             patch('search_flow.extract_structured_data') as mock_data, \
             patch('search_flow.get_connection') as mock_db:
            
            # Mock database cursor and operations
            mock_cursor = MagicMock()
            mock_db.return_value.__enter__.return_value.cursor.return_value = mock_cursor
            
            # Mock checkpoint query response
            mock_cursor.fetchone.side_effect = [
                (CHECKPOINT_STAGES['CONTEXT'], json.dumps({'company_context': 'test context'}), 0),
                (1,),  # For any other fetchone calls
                None   # For subsequent calls
            ]
            
            mock_queries.return_value = [{
                'category': 'environmental_safety',
                'query': 'test query',
                'rationale': 'test',
                'priority': 1
            }]
            mock_search.return_value = [{
                'title': 'test',
                'url': 'http://test.com',
                'source_hash': 'abc123',
                'snippet': 'test snippet',
                'domain': 'test.com',
                'source_type': 'web',
                'category': 'environmental_safety',
                'query_context': 'test query',
                'retrieved_at': datetime.now(timezone.utc).isoformat(),
                'published_date': None
            }]
            mock_news.return_value = [{
                'title': 'test news',
                'url': 'http://test.com',
                'source_hash': 'def456',
                'snippet': 'test news snippet',
                'domain': 'test.com',
                'source_type': 'news',
                'category': 'environmental_safety',
                'query_context': 'test query',
                'retrieved_at': datetime.now(timezone.utc).isoformat(),
                'published_date': '2024-01-01'
            }]
            mock_summary.return_value = "test summary"
            mock_data.return_value = {'risk_score': 50}
            
            # Mock database operations
            mock_cursor.execute.return_value = None
            mock_cursor.fetchall.return_value = []
            
            result = self.workflow.research_company(self.test_company)
            
            # Verify that get_company_context wasn't called (should use checkpoint)
            mock_context.assert_not_called()
            self.assertIsNotNone(result)
    
    def test_max_retries(self):
        """Test that max retries is enforced"""
        # Simulate multiple failures
        for _ in range(4):  # More than max_retries
            self.workflow._update_checkpoint(
                self.test_company['ticker'],
                CHECKPOINT_STAGES['CONTEXT'],
                {'company_context': 'test context'},
                error="Test error"
            )
        
        # Try to research the company
        result = self.workflow.research_company(self.test_company, max_retries=3)
        self.assertIsNone(result)  # Should return None due to max retries
    
    def test_research_status(self):
        """Test research status reporting"""
        # Create some test companies with different stages
        companies = [
            ("TEST1", CHECKPOINT_STAGES['COMPLETE'], 0),  # Completed
            ("TEST2", CHECKPOINT_STAGES['CONTEXT'], 0),   # In progress
            ("TEST3", CHECKPOINT_STAGES['CONTEXT'], 3),   # Failed (max retries)
            ("TEST4", None, 0)                           # Not started
        ]
        
        with patch('search_flow.get_connection') as mock_db:
            mock_cursor = MagicMock()
            mock_db.return_value.__enter__.return_value.cursor.return_value = mock_cursor
            
            # Mock the status query results
            mock_cursor.fetchone.return_value = (4, 1, 1, 1, 1)  # total, completed, not_started, in_progress, failed
            
            status = get_research_status()
            self.assertEqual(status['completed'], 1)
            self.assertEqual(status['in_progress'], 1)
            self.assertEqual(status['failed'], 1)
            self.assertEqual(status['not_started'], 1)
            self.assertEqual(status['total'], 4)
    
    def test_incomplete_research_list(self):
        """Test getting list of incomplete research"""
        # Create some test data
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO companies (name, ticker, tick)
                VALUES ('Test Inc', 'TEST', 50)
            """)
            conn.commit()
        
        # Should be in incomplete list (not started)
        incomplete = get_incomplete_research()
        self.assertTrue(any(c['ticker'] == 'TEST' for c in incomplete))
        
        # Mark as complete
        self.workflow._update_checkpoint('TEST', CHECKPOINT_STAGES['COMPLETE'], {})
        
        # Should not be in incomplete list
        incomplete = get_incomplete_research()
        self.assertFalse(any(c['ticker'] == 'TEST' for c in incomplete))

    def tearDown(self):
        """Clean up test data"""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM research_checkpoints WHERE company_ticker LIKE 'TEST%'")
            cursor.execute("DELETE FROM companies WHERE ticker LIKE 'TEST%'")
            conn.commit()

if __name__ == '__main__':
    unittest.main() 