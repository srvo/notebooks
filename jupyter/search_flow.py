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

    def process_search(self, query: str):
        """Process a search query"""
        try:
            logger.info(f"Starting search flow for query: {query}")
            # Fetch data from API
            data = self.api_client.fetch_data('search_endpoint', params={'query': query})
            logger.debug("Fetched data from API")

            # Process data
            processed_data = self.data_processor.process(data)
            logger.debug("Processed data")

            # Save processed data
            self.data_store.save_to_db(processed_data)
            logger.info("Processed data saved to database.")

            # Backup database
            self.data_store.backup_to_s3('data/research.db')
            logger.info("Database backed up to S3.")

        except Exception as e:
            logger.critical(f"Critical error in search_flow: {e}")
            raise

