#!/usr/bin/env python3
import argparse
from search_flow import SearchFlow
from logger import setup_logger


def parse_arguments():
    parser = argparse.ArgumentParser(description='Run search flow as a background process.')
    parser.add_argument('--reset', action='store_true', help='Reset the research database.')
    parser.add_argument('--query', type=str, required=True, help='Search query to process')
    return parser.parse_args()

def main():
    args = parse_arguments()
    # Initialize components
    api_client = APIClient()
    data_store = DataStore()
    data_processor = DataProcessor()
    search_flow = SearchFlow(api_client, data_store, data_processor)

    if args.reset:
        # Logic to reset the database
        logger.info("Resetting the research database.")
        # Example:
        # data_store.reset_database()
    
    try:
        search_flow.process_search(args.query)
        logger.info("Background search completed successfully.")
    except Exception as e:
        logger.error(f"Background search failed: {e}")

if __name__ == '__main__':
    main()
