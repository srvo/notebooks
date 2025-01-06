from .base import ResearchWorkflow
from typing import Dict, List
import logging
import json
import csv
from datetime import datetime
import duckdb
from pathlib import Path
from ..engines import DuckDuckGoEngine, DeepSeekEngine

logger = logging.getLogger(__name__)

class EthicalAnalysisWorkflow(ResearchWorkflow):
    def __init__(self):
        self.search_engine = DuckDuckGoEngine()
        self.analysis_engine = DeepSeekEngine()
        
    def build_query(self, company: dict) -> str:
        # Extract relevant fields
        name = company['Company']
        category = company.get('Category', '')
        criteria = company.get('Criteria', '')
        
        # Build query components
        components = [name]
        if category:
            components.append(category)
        if criteria:
            components.append(criteria)
        components.extend(["ethical", "controversies", "violations"])
        
        # Combine into search query
        query = " ".join(components)
        logger.debug(f"Built query for {name}: {query}")
        return query
    
    def setup_database(self, db_path):
        con = duckdb.connect(':memory:')
        try:
            con.execute("""
                CREATE TABLE IF NOT EXISTS searches (
                    timestamp TIMESTAMP,
                    query VARCHAR,
                    num_results INTEGER
                )
            """)
            
            con.execute("""
                CREATE TABLE IF NOT EXISTS search_results (
                    timestamp TIMESTAMP,
                    query VARCHAR,
                    title VARCHAR,
                    link VARCHAR,
                    snippet VARCHAR,
                    source VARCHAR
                )
            """)
            
            con.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    timestamp TIMESTAMP,
                    query VARCHAR,
                    analysis JSON
                )
            """)
            
            return con
        except Exception as e:
            logger.error(f"Database setup error: {str(e)}", exc_info=True)
            con.close()
            raise
    
    def word_count(self, text: str) -> int:
        return len(str(text).split())
    
    def read_exclusions(self, file_path):
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            return list(reader)
    
    def execute(self, data_dir: str = "data") -> Dict:
        data_dir = Path(data_dir)
        data_dir.mkdir(exist_ok=True)
        
        # Read exclusions
        exclusions = self.read_exclusions(data_dir / "exclude.csv")
        logger.info(f"Found {len(exclusions)} companies to analyze")
        
        # Setup database
        db_path = data_dir / "research.db"
        con = self.setup_database(db_path)
        
        total_snippet_words = 0
        total_analysis_words = 0
        results_by_company = {}
        
        # Process each company
        for idx, company in enumerate(exclusions, 1):
            company_name = company['Company']
            query = self.build_query(company)
            logger.info(f"Processing {idx}/{len(exclusions)}: {company_name}")
            logger.info(f"Query: {query}")
            
            try:
                # Run search and analysis
                search_results = self.search_engine.search(query)
                results = {
                    'query': query,
                    'results': search_results,
                    'analysis': self.analysis_engine.analyze(search_results)
                }
                
                # Store in results dict
                results_by_company[company_name] = results
                
                # Insert into database
                now = datetime.now()

                con.execute("""
                    INSERT INTO searches (timestamp, query, num_results)
                    VALUES (?, ?, ?)
                """, [now, query, len(search_results)])
                
                for result in search_results:
                    con.execute("""
                        INSERT INTO search_results (timestamp, query, title, link, snippet, source)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, [now, query, result['title'], result['link'], result['snippet'], result['source']])
                
                con.execute("""
                    INSERT INTO analyses (timestamp, query, analysis)
                    VALUES (?, ?, ?)
                """, [now, query, json.dumps(results['analysis'])])
                
                # Update word counts
                snippet_words = sum(self.word_count(result['snippet']) for result in search_results)
                analysis_words = self.word_count(results['analysis'].get('content', ''))
                total_snippet_words += snippet_words
                total_analysis_words += analysis_words
                
                logger.info(f"""
    Processed {company_name}:
    - Search Results: {len(search_results)} records ({snippet_words} words in snippets)
    - Analysis: {analysis_words} words
                """.strip())
                
            except Exception as e:
                logger.error(f"Error processing {company_name}: {str(e)}", exc_info=True)
                continue

        # Save combined results to a single JSON file
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        combined_results = {
            "meta": {
                "timestamp": datetime.now().isoformat(),
                "version": "1.0",
                "type": "ethical_analysis"
            },
            "companies": [
                {
                    "company_name": company_name,
                    "symbol": company.get('Symbol', ''),
                    "primary_category": company.get('Category', ''),
                    "current_criteria": company.get('Criteria', ''),
                    "analysis": {
                        "historical": results['analysis'],
                        "evidence": {
                            "sources": results['results'],
                            "query": results['query']
                        },
                        "categorization": {
                            "product_issues": [],
                            "conduct_issues": [],
                            "tags": [],
                            "patterns": {}
                        }
                    },
                    "metadata": {
                        "analysis_timestamp": datetime.now().isoformat(),
                        "data_confidence": None,
                        "pattern_confidence": None
                    }
                }
                for company_name, results in results_by_company.items()
            ]
        }
        
        json_path = data_dir / f"ethical_analysis_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(combined_results, f, indent=2)
        logger.info(f"Saved combined analysis results to {json_path}")
        
        # Log final stats
        search_count = con.execute("SELECT COUNT(*) FROM searches").fetchone()[0]
        results_count = con.execute("SELECT COUNT(*) FROM search_results").fetchone()[0]
        analyses_count = con.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
        
        stats = {
            'companies_processed': len(exclusions),
            'total_searches': search_count,
            'total_results': results_count,
            'total_snippet_words': total_snippet_words,
            'total_analyses': analyses_count,
            'total_analysis_words': total_analysis_words
        }
        
        logger.info(f"""
Final Database Stats:
- Companies Processed: {stats['companies_processed']}
- Total Searches: {stats['total_searches']} records
- Total Search Results: {stats['total_results']} records ({stats['total_snippet_words']} words in snippets)
- Total Analyses: {stats['total_analyses']} records ({stats['total_analysis_words']} words in analyses)
DuckDB saved to: {db_path}
        """.strip())
        
        con.close()
        return {'stats': stats, 'results': results_by_company} 