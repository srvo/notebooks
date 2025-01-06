#!/usr/bin/env python3
import pandas as pd
import logging
from datetime import datetime
import os
from db import get_connection
import json
import subprocess
from pathlib import Path

# Enhanced logging setup
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_dir, f"ethical_analysis_{timestamp}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(funcName)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

def sync_to_s3():
    """Sync the database to S3 using rclone"""
    date_str = datetime.now().strftime("%y%m%d")
    s3_path = f"flows/ethical_analysis/{date_str}.db"
    
    # Configure rclone with Hetzner credentials
    rclone_config = f"""
    [hetzner]
    type = s3
    provider = Other
    access_key_id = {os.getenv('HETZNER_S3_ACCESS_KEY')}
    secret_access_key = {os.getenv('HETZNER_S3_SECRET_KEY')}
    endpoint = {os.getenv('S3_DATA_BUCKET')}
    """
    
    # Write temporary rclone config
    config_path = Path.home() / '.config' / 'rclone' / 'rclone.conf'
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, 'w') as f:
        f.write(rclone_config)
    
    try:
        logging.info(f"Syncing database to S3: {s3_path}")
        subprocess.run([
            'rclone',
            'copy',
            'data/research.db',
            f'hetzner:{s3_path}'
        ], check=True)
        logging.info("S3 sync complete")
    except Exception as e:
        logging.error(f"Failed to sync to S3: {str(e)}")
    finally:
        # Clean up config
        config_path.unlink(missing_ok=True)

def setup_analysis_tables():
    """Create tables for storing ethical analysis results"""
    with get_connection() as conn:
        cursor = conn.cursor()
        logging.info("Setting up/verifying database tables")
        
        # Main analysis table - one row per controversy/issue
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ethical_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            symbol TEXT,
            
            -- Primary categorization
            primary_category TEXT,  -- 'product-based' or 'conduct-based'
            issue_type TEXT,        -- specific category (e.g., 'animal cruelty', 'corruption')
            
            -- Detailed analysis
            description TEXT,       -- full description of the issue
            historical_pattern TEXT, -- pattern of behavior over time
            stakeholder_impact TEXT, -- who was affected and how
            
            -- Evidence
            sources TEXT,           -- JSON array of sources
            earliest_known_date DATE,
            latest_known_date DATE,
            
            -- Severity metrics
            severity_score INTEGER,  -- 1-10
            pattern_score INTEGER,   -- 1-10, how systematic/repeated
            evidence_strength INTEGER, -- 1-10, how well documented
            
            -- Tags and metadata
            tags TEXT,              -- JSON array of relevant tags
            related_issues TEXT,     -- JSON array of related controversy IDs
            notes TEXT,
            
            analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        logging.info("Created/verified ethical_analysis table")
        
        # Aggregated company metrics
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_ethical_profile (
            company_name TEXT PRIMARY KEY,
            symbol TEXT,
            
            -- Overall metrics
            total_issues INTEGER,
            avg_severity FLOAT,
            max_severity INTEGER,
            
            -- Category breakdowns
            product_issues TEXT,    -- JSON object of product-based issues
            conduct_issues TEXT,    -- JSON object of conduct-based issues
            
            -- Timeline
            earliest_controversy DATE,
            latest_controversy DATE,
            controversy_frequency TEXT, -- JSON object with temporal analysis
            
            -- Pattern analysis
            primary_concerns TEXT,      -- JSON array of main ethical concerns
            recurring_patterns TEXT,    -- JSON object of behavioral patterns
            stakeholder_impacts TEXT,   -- JSON object of affected groups
            
            -- Meta analysis
            data_confidence_score INTEGER,  -- 1-10, how complete is our data
            pattern_confidence_score INTEGER, -- 1-10, how clear are the patterns
            
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        logging.info("Created/verified company_ethical_profile table")
        conn.commit()

def generate_analysis_prompt(company_row):
    """Generate a structured prompt for comprehensive ethical analysis"""
    prompt = f"""Analyze the ethical profile and history of {company_row['Company']} ({company_row['Symbol']}). 
    Current primary exclusion: {company_row['Category']} - {company_row['Criteria']}

    Please provide a comprehensive ethical analysis with the following structure:

    1. HISTORICAL ANALYSIS (40%):
    - Detailed timeline of controversies and ethical issues
    - Patterns of behavior and recurring issues
    - Evolution of company practices over time
    - Relationships between different ethical concerns

    2. EVIDENCE AND DOCUMENTATION (30%):
    - Specific incidents with dates
    - Primary sources and documentation
    - Regulatory actions and legal cases
    - Third-party investigations and reports
    - Stakeholder testimonies and impacts

    3. CATEGORIZATION AND METADATA (30%):
    
    A. Primary Categories:
    - Product-based issues (e.g., weapons, animal products, fossil fuels)
    - Conduct-based issues (e.g., corruption, labor violations, environmental damage)
    
    B. Specific Tags:
    - Issue types (e.g., animal cruelty, corruption, labor violations)
    - Affected stakeholders (e.g., workers, communities, environment)
    - Geographic scope
    - Severity indicators
    
    C. Pattern Analysis:
    - Systematic vs isolated issues
    - Response patterns to controversies
    - Corporate culture indicators
    - Governance implications

    Please provide as much detail as available. Don't limit the response length - thoroughness is preferred."""
    
    logging.info(f"Generated analysis prompt for {company_row['Company']}")
    return prompt

def save_analysis_json(company_data, timestamp):
    """Save analysis results as JSON"""
    date_str = timestamp.strftime("%y%m%d_%H%M%S")
    json_dir = Path("data/analysis_json")
    json_dir.mkdir(parents=True, exist_ok=True)
    
    # Save local JSON
    json_path = json_dir / f"ethical_analysis_{date_str}.json"
    with open(json_path, 'w') as f:
        json.dump(company_data, f, indent=2)
    logging.info(f"Saved analysis JSON to {json_path}")
    
    # Sync to S3
    s3_path = f"flows/ethical_analysis/{date_str}.json"
    try:
        logging.info(f"Syncing JSON to S3: {s3_path}")
        subprocess.run([
            'rclone',
            'copy',
            str(json_path),
            f'hetzner:{s3_path}'
        ], check=True)
        logging.info("S3 JSON sync complete")
    except Exception as e:
        logging.error(f"Failed to sync JSON to S3: {str(e)}")

def run_ethical_analysis():
    """Main function to run the ethical analysis flow"""
    run_timestamp = datetime.now()
    analysis_results = {
        "meta": {
            "timestamp": run_timestamp.isoformat(),
            "version": "1.0",
            "type": "ethical_analysis"
        },
        "companies": []
    }
    
    try:
        logging.info("Starting comprehensive ethical analysis flow")
        
        # Read exclude list
        logging.info("Reading exclude.csv")
        df = pd.read_csv('data/exclude.csv')
        logging.info(f"Found {len(df)} companies to analyze")
        
        # Setup database tables (keep this for querying purposes)
        setup_analysis_tables()
        
        # Process each company
        for idx, row in df.iterrows():
            try:
                company_name = row['Company']
                symbol = row['Symbol']
                logging.info(f"[{idx+1}/{len(df)}] Starting analysis of {company_name} ({symbol})")
                
                # Generate and run analysis
                prompt = generate_analysis_prompt(row)
                logging.info(f"Running search and analysis for {company_name}")
                
                # TODO: Implement actual search/analysis logic here
                # For now, creating placeholder structured data
                company_analysis = {
                    "company_name": company_name,
                    "symbol": symbol,
                    "primary_category": row['Category'],
                    "current_criteria": row['Criteria'],
                    "analysis": {
                        "historical": {},
                        "evidence": {},
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
                
                # Add to our results collection
                analysis_results["companies"].append(company_analysis)
                
                # Still update DuckDB for querying purposes
                with get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                    INSERT INTO ethical_analysis 
                    (company_name, symbol, primary_category, issue_type, description)
                    VALUES (?, ?, ?, ?, ?)
                    """, (
                        company_name,
                        symbol,
                        row['Category'],
                        row['Criteria'],
                        json.dumps(company_analysis)  # Store full analysis as JSON
                    ))
                    conn.commit()
                
                logging.info(f"Completed analysis of {company_name}")
                
                # Save JSON periodically (every 10 companies)
                if (idx + 1) % 10 == 0:
                    save_analysis_json(analysis_results, run_timestamp)
                
            except Exception as e:
                logging.error(f"Error processing {company_name}: {str(e)}", exc_info=True)
                continue
        
        # Final JSON save at completion
        save_analysis_json(analysis_results, run_timestamp)
        logging.info("Ethical analysis flow complete")
        
    except Exception as e:
        logging.error(f"Fatal error in ethical analysis flow: {str(e)}", exc_info=True)
        # Try to save what we have even if we crashed
        save_analysis_json(analysis_results, run_timestamp)
        raise

if __name__ == "__main__":
    try:
        logging.info("=== Starting Ethical Analysis Process ===")
        logging.info(f"Log file: {log_file}")
        run_ethical_analysis()
    except Exception as e:
        logging.error("Process failed with error", exc_info=True) 