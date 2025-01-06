from api_client import APIClient
from data_store import DataStore
from data_processor import DataProcessor
from logger import setup_logger

logger = setup_logger('search_flow', 'logs/search_flow.log')

class SearchFlow:
    def __init__(self, api_client: APIClient = None, data_store: DataStore = None, 
                 data_processor: DataProcessor = None):
        self.api_client = api_client or APIClient()
        self.data_store = data_store or DataStore()
        self.data_processor = data_processor or DataProcessor()
        logger.debug("Initialized SearchFlow with API client, data store, and data processor")

    def process_search(self, query: str):
        """Process a search query"""
        try:
            # Fetch data from API
            data = self.api_client.fetch_data('search_endpoint', params={'query': query})
            logger.info(f"Data fetched for query: {query}")

            # Process data
            processed_data = self.data_processor.process(data)

            # Save processed data to database
            self.data_store.save_to_db(processed_data)
            logger.info("Processed data saved to database.")

            # Backup database to S3
            self.data_store.backup_to_s3('data/research.db')
            logger.info("Database backed up to S3.")

        except Exception as e:
            logger.critical(f"Critical error in search_flow: {e}")
            raise

