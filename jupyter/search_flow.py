from api_client import APIClient
from data_store import DataStore
from data_processor import DataProcessor
from logger import setup_logger

logger = setup_logger('search_flow', 'logs/search_flow.log')

class SearchFlow:
    def __init__(self, api_client: APIClient, data_store: DataStore, data_processor: DataProcessor):
        self.api_client = api_client
        self.data_store = data_store
        self.data_processor = data_processor
        logger.debug("Initialized SearchFlow with API client, data store, and data processor")

    def fetch_data(self, query: str):
        """Fetch data from API"""
        try:
            logger.info(f"Fetching data for query: {query}")
            return self.api_client.fetch_data('search_endpoint', params={'query': query})
        except Exception as e:
            logger.error(f"Failed to fetch data: {e}")
            raise

    def process_data(self, data):
        """Process raw data"""
        try:
            logger.debug("Processing data")
            return self.data_processor.process(data)
        except Exception as e:
            logger.error(f"Failed to process data: {e}")
            raise

    def save_data(self, processed_data):
        """Save processed data to database and backup to S3"""
        try:
            logger.debug("Saving processed data")
            self.data_store.save_to_db(processed_data)
            self.data_store.backup_to_s3('data/research.db')
            logger.info("Data saved and backed up successfully.")
        except Exception as e:
            logger.error(f"Failed to save data: {e}")
            raise

    def process_search(self, query: str):
        """Process a search query"""
        try:
            logger.info(f"Starting search flow for query: {query}")
            data = self.fetch_data(query)
            processed_data = self.process_data(data)
            self.save_data(processed_data)
            logger.info("Search flow completed successfully.")
        except Exception as e:
            logger.critical(f"Critical error in search_flow: {e}")
            raise

