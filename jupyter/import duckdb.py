from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import duckdb
from pathlib import Path
import os

# Environment setup
PROJECT_ROOT = Path(os.getenv('PROJECT_ROOT', '/Users/srvo/notebooks'))
DATA_DIR = PROJECT_ROOT / 'data'
DB_PATH = DATA_DIR / 'research.db'

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

@dataclass
class CompanyBasicInfo:
    name: str
    industry: Optional[str] = None
    headquarters: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    founded: Optional[str] = None
    
@dataclass
class ResearchFindings:
    timestamp: str
    source: str
    category: str  # environmental_safety, financial_legal, ethical_social
    summary: str
    url: Optional[str] = None
    relevance_score: Optional[float] = None

class ResearchDB:
    """Database manager for company research"""
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.conn = duckdb.connect(str(db_path))
        self.init_schema()
    
    def init_schema(self):
        """Initialize database schema with version tracking"""
        # Schema version tracking
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_versions (
                version_id VARCHAR PRIMARY KEY,
                applied_at TIMESTAMP,
                description TEXT
            )
        """)
        
        # Core tables
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY,
                name VARCHAR UNIQUE,
                industry VARCHAR,
                headquarters VARCHAR,
                description TEXT,
                website VARCHAR,
                founded VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS research_findings (
                id INTEGER PRIMARY KEY,
                company_id INTEGER,
                category VARCHAR,
                summary TEXT,
                source VARCHAR,
                url VARCHAR,
                relevance_score FLOAT,
                raw_data JSON,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS search_queries (
                id INTEGER PRIMARY KEY,
                company_id INTEGER,
                category VARCHAR,
                query_text TEXT,
                source_type VARCHAR,
                parameters JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        """)
        
        # Record schema version
        self.conn.execute("""
            INSERT INTO schema_versions (version_id, applied_at, description)
            VALUES (?, CURRENT_TIMESTAMP, ?)
            ON CONFLICT (version_id) DO NOTHING
        """, ('1.0', 'Initial schema with companies, findings, and search queries'))
    
    def add_company(self, company_info: CompanyBasicInfo) -> int:
        """Add or update a company in the database"""
        try:
            # Check if company exists
            existing = self.conn.execute(
                "SELECT id FROM companies WHERE name = ?", 
                (company_info.name,)
            ).fetchone()
            
            if existing:
                # Update existing company
                self.conn.execute("""
                    UPDATE companies 
                    SET industry = ?,
                        headquarters = ?,
                        description = ?,
                        website = ?,
                        founded = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    company_info.industry,
                    company_info.headquarters,
                    company_info.description,
                    company_info.website,
                    company_info.founded,
                    existing[0]
                ))
                return existing[0]
            else:
                # Insert new company
                result = self.conn.execute("""
                    INSERT INTO companies (
                        name, industry, headquarters, description, website, founded
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    RETURNING id
                """, (
                    company_info.name,
                    company_info.industry,
                    company_info.headquarters,
                    company_info.description,
                    company_info.website,
                    company_info.founded
                )).fetchone()
                return result[0]
        except Exception as e:
            print(f"Error managing company: {str(e)}")
            return None
    
    def add_finding(self, company_id: int, finding: ResearchFindings, raw_data: Dict = None):
        """Add a research finding for a company"""
        try:
            self.conn.execute("""
                INSERT INTO research_findings 
                (company_id, category, summary, source, url, relevance_score, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                company_id,
                finding.category,
                finding.summary,
                finding.source,
                finding.url,
                finding.relevance_score,
                json.dumps(raw_data) if raw_data else None
            ))
        except Exception as e:
            print(f"Error adding finding: {str(e)}")
    
    def get_company_findings(self, company_name: str, category: str = None) -> List[Dict]:
        """Get findings for a company, optionally filtered by category"""
        try:
            query = """
                SELECT 
                    f.*,
                    c.name as company_name
                FROM research_findings f
                JOIN companies c ON f.company_id = c.id
                WHERE c.name = ?
            """
            params = [company_name]
            
            if category:
                query += " AND f.category = ?"
                params.append(category)
                
            query += " ORDER BY f.discovered_at DESC"
            
            results = self.conn.execute(query, params).fetchall()
            
            return [dict(zip(['id', 'company_id', 'category', 'summary', 'source', 
                            'url', 'relevance_score', 'raw_data', 'discovered_at', 
                            'company_name'], row)) 
                   for row in results]
        except Exception as e:
            print(f"Error getting findings: {str(e)}")
            return []

# Example usage
if __name__ == "__main__":
    # Initialize database
    db = ResearchDB()
    
    # Add a test company
    tesla_info = CompanyBasicInfo(
        name="Tesla",
        industry="Automotive & Energy",
        headquarters="Austin, Texas",
        website="tesla.com",
        founded="2003",
        description="Electric vehicle and clean energy company"
    )
    
    company_id = db.add_company(tesla_info)
    
    # Add a test finding
    finding = ResearchFindings(
        timestamp=datetime.now().isoformat(),
        source="EPA Database",
        category="environmental_safety",
        summary="Environmental impact assessment for Gigafactory",
        url="https://example.com/report",
        relevance_score=0.85
    )
    
    raw_data = {
        "document_type": "impact_assessment",
        "facility": "Gigafactory Texas",
        "assessment_date": "2023-12-01",
        "key_findings": ["water usage concerns", "wildlife impact mitigation"]
    }
    
    db.add_finding(company_id, finding, raw_data)
    
    # Retrieve and print findings
    findings = db.get_company_findings("Tesla", category="environmental_safety")
    print("\nTesla Environmental Safety Findings:")
    for f in findings:
        print(f"\nCategory: {f['category']}")
        print(f"Summary: {f['summary']}")
        print(f"Source: {f['source']}")
        print(f"Relevance: {f['relevance_score']}")
        if f['raw_data']:
            print("Raw Data:", f['raw_data'])