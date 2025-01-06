from logger import setup_logger

logger = setup_logger('database_reset', 'logs/database_reset.log')

class DatabaseResetter:
    def __init__(self, data_store):
        self.data_store = data_store

    def reset_research_tables(self):
        """Reset all research-related database tables"""
        try:
            with self.data_store.engine.connect() as conn:
                tables = ['research_checkpoints', 'research_sources', 'research_results']
                for table in tables:
                    conn.execute(f'DELETE FROM {table}')
                    logger.info(f'Cleared {table}')
                conn.commit()
                logger.info('Research data reset complete.')
        except Exception as e:
            logger.error(f'Error resetting research tables: {str(e)}')
            raise
