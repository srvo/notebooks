#!/usr/bin/env python3
import argparse
from api_client import APIClient
from data_store.py import DataStore
from logger import setup_logger

logger = setup_logger('run_background_search', 'logs/run_background_search.log')

def parse_arguments():
    parser = argparse.ArgumentParser(description='Run search flow as a background process.')
    parser.add_argument('--reset', action='store_true', help='Reset the research database.')
    return parser.parse_args()

def main():
    args = parse_arguments()
    api_client = APIClient()
    data_store = DataStore()

    if args.reset:
        # Logic to reset the database
        logger.info("Resetting the research database.")
        # Example:
        # data_store.reset_database()
    
    try:
        # Example endpoint and parameters
        data = api_client.fetch_data('search_endpoint', params={'query': 'research'})
        data_store.save_to_db(data)
        data_store.backup_to_s3('data/research.db')
        logger.info("Background search completed successfully.")
    except Exception as e:
        logger.error(f"Background search failed: {e}")

if __name__ == '__main__':
    main()
