import os

class Config:
    # API Configuration
    API_BASE_URL = os.getenv('API_BASE_URL', 'https://api.example.com')
    API_KEY = os.getenv('API_KEY', 'your_api_key')

    # Database Configuration
    DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///data/research.db')

    # S3 Configuration
    S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'your-s3-bucket-name')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', 'your_access_key')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', 'your_secret_key')
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1') 