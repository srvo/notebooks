from db import get_connection
from logger import setup_logger

logger = setup_logger('reset_research', 'logs/reset_research.log')

def reset_research_data():
    """Reset all research-related database tables"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Delete data from research tables
        tables = ['research_checkpoints', 'research_sources', 'research_results']
        for table in tables:
            try:
                cursor.execute(f'DELETE FROM {table}')
                logger.info(f'Cleared {table}')
            except Exception as e:
                logger.error(f'Error clearing {table}: {str(e)}')
        
        conn.commit()
        logger.info('Research data reset complete.')

if __name__ == "__main__":
    reset_research_data()
