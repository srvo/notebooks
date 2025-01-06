from data_store import DataStore
from database_reset import DatabaseResetter
from logger import setup_logger

logger = setup_logger('reset_research', 'logs/reset_research.log')

if __name__ == "__main__":
    data_store = DataStore()
    resetter = DatabaseResetter(data_store)
    resetter.reset_research_tables()
