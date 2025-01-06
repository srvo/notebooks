import logging
import json
import csv
from datetime import datetime
import duckdb
from pathlib import Path
from research.engines import DuckDuckGoEngine, DeepSeekEngine
from research.workflow import SearchWorkflow

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_database(db_path):
    # Use in-memory database for now
    con = duckdb.connect(':memory:')
    try:
        # Create tables if they don't exist
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

def word_count(text: str) -> int:
    return len(str(text).split())

def read_exclusions(file_path):
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        return list(reader)

def build_query(company: dict) -> str:
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

def main():
    # Create data directory if it doesn't exist
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Initialize engines and workflow
    search_engine = DuckDuckGoEngine()
    analysis_engine = DeepSeekEngine()
    workflow = SearchWorkflow(search_engine, analysis_engine)
    
    # Read exclusions
    exclusions = read_exclusions(data_dir / "exclude.csv")
    logger.info(f"Found {len(exclusions)} companies to analyze")
    
    # Setup database
    db_path = data_dir / "research.db"
    con = setup_database(db_path)
    
    total_snippet_words = 0
    total_analysis_words = 0
    
    # Process each company
    for idx, company in enumerate(exclusions, 1):
        company_name = company['Company']
        query = build_query(company)
        logger.info(f"Processing {idx}/{len(exclusions)}: {company_name}")
        logger.info(f"Query: {query}")
        
        try:
            # Run search and analysis
            results = workflow.run(query)
            
            # Save to JSON
            timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
            json_path = data_dir / f"ethical_analysis_{company_name.replace(' ', '_')}_{timestamp}.json"
            with open(json_path, 'w') as f:
                json.dump(results, f, indent=2)
            
            # Insert into database
            now = datetime.now()
            
            con.execute("""
                INSERT INTO searches (timestamp, query, num_results)
                VALUES (?, ?, ?)
            """, [now, query, len(results['results'])])
            
            for result in results['results']:
                con.execute("""
                    INSERT INTO search_results (timestamp, query, title, link, snippet, source)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, [now, query, result['title'], result['link'], result['snippet'], result['source']])
            
            con.execute("""
                INSERT INTO analyses (timestamp, query, analysis)
                VALUES (?, ?, ?)
            """, [now, query, json.dumps(results['analysis'])])
            
            # Update word counts
            snippet_words = sum(word_count(result['snippet']) for result in results['results'])
            analysis_words = word_count(results['analysis'].get('content', ''))
            total_snippet_words += snippet_words
            total_analysis_words += analysis_words
            
            logger.info(f"""
Processed {company_name}:
- Search Results: {len(results['results'])} records ({snippet_words} words in snippets)
- Analysis: {analysis_words} words
            """.strip())
            
        except Exception as e:
            logger.error(f"Error processing {company_name}: {str(e)}", exc_info=True)
            continue
    
    # Log final stats
    search_count = con.execute("SELECT COUNT(*) FROM searches").fetchone()[0]
    results_count = con.execute("SELECT COUNT(*) FROM search_results").fetchone()[0]
    analyses_count = con.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
    
    logger.info(f"""
Final Database Stats:
- Companies Processed: {len(exclusions)}
- Total Searches: {search_count} records
- Total Search Results: {results_count} records ({total_snippet_words} words in snippets)
- Total Analyses: {analyses_count} records ({total_analysis_words} words in analyses)
DuckDB saved to: {db_path}
    """.strip())
    
    con.close()

if __name__ == "__main__":
    main() 