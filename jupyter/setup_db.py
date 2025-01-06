import sqlite3
from pathlib import Path

# Setup database path
DATABASE_PATH = Path("/Users/srvo/notebooks/data/research.db")

def setup_database():
    """Create research database tables if they don't exist"""
    # Ensure the data directory exists
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Create database connection
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        # Create companies table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY,
                name VARCHAR NOT NULL,
                ticker VARCHAR,
                isin VARCHAR,
                tick INTEGER,
                industry VARCHAR,
                category VARCHAR,
                sector VARCHAR,
                description TEXT,
                last_tick_date DATE,
                workflow VARCHAR,
                excluded BOOLEAN DEFAULT FALSE,
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        print("Database tables created successfully!")
    finally:
        conn.close()

if __name__ == "__main__":
    setup_database() 