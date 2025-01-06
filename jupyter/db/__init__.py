from pathlib import Path
import os
from dotenv import load_dotenv
import sqlite3
from contextlib import contextmanager

# Load environment variables
load_dotenv()

# Setup paths
PROJECT_ROOT = Path(os.getenv('PROJECT_ROOT', '/Users/srvo/notebooks'))
DATA_DIR = PROJECT_ROOT / 'data'
DB_PATH = DATA_DIR / 'research.db'

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

@contextmanager
def get_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.commit()
        conn.close()

def execute_query(query, params=None):
    """Execute a query and return results"""
    with get_connection() as conn:
        if params:
            return conn.execute(query, params).fetchall()
        return conn.execute(query).fetchall()

def insert_company(name, industry=None, headquarters=None, description=None, website=None, founded=None):
    """Insert a new company"""
    query = """
        INSERT INTO companies (name, industry, headquarters, description, website, founded)
        VALUES (?, ?, ?, ?, ?, ?)
        RETURNING id
    """
    result = execute_query(query, (name, industry, headquarters, description, website, founded))
    return result[0][0] if result else None

def get_company(name):
    """Get company by name"""
    query = "SELECT * FROM companies WHERE name = ?"
    result = execute_query(query, (name,))
    return result[0] if result else None 