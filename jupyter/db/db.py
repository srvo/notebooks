import sqlite3
from contextlib import contextmanager
from pathlib import Path

DATABASE_PATH = Path("/Users/srvo/notebooks/data/research.db")

@contextmanager
def get_connection():
    """Create a database connection context manager"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.commit()
        conn.close()

def insert_company(conn, company_data):
    """Insert a company into the database"""
    query = """
        INSERT INTO companies (
            name, ticker, isin, tick, industry, category, 
            sector, description, last_tick_date, workflow, 
            excluded, note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (name) DO UPDATE SET
            ticker=excluded.ticker,
            tick=excluded.tick,
            last_tick_date=excluded.last_tick_date,
            note=excluded.note
        RETURNING id
    """
    return conn.execute(query, company_data).fetchone()
