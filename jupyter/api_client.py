import requests
from config import Config
from logger import setup_logger

logger = setup_logger('api_client', 'logs/api_client.log')

class APIClient:
    def __init__(self):
        self.base_url = Config.API_BASE_URL
        self.headers = {'Authorization': f'Bearer {Config.API_KEY}'}

    def fetch_data(self, endpoint: str, params: dict = None):
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            logger.debug(f"Fetching data from {url} with params: {params}")
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            logger.info(f"Successfully fetched data from {url}")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise
from config import Config
from logger import setup_logger

logger = setup_logger('api_client', 'logs/api_client.log')

class APIClient:
    def __init__(self):
        self.base_url = Config.API_BASE_URL
        self.headers = {'Authorization': f'Bearer {Config.API_KEY}'}

    def fetch_data(self, endpoint: str, params: dict = None):
        """Fetch data from API endpoint"""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            logger.info(f"Fetched data from {url}")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise
