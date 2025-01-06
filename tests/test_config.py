import os
from jupyter.config import Config

def test_config_default_values():
    """Test default configuration values."""
    config = Config()
    
    assert config.API_BASE_URL == 'https://api.example.com'
    assert config.API_KEY == 'your_api_key'
    assert config.DATABASE_URI == 'sqlite:///data/research.db'
    assert config.S3_BUCKET_NAME == 'your-s3-bucket-name'
    assert config.AWS_ACCESS_KEY_ID == 'your_access_key'
    assert config.AWS_SECRET_ACCESS_KEY == 'your_secret_key'
    assert config.AWS_REGION == 'us-east-1'

def test_config_environment_variables(monkeypatch):
    """Test configuration with environment variables."""
    monkeypatch.setenv('API_BASE_URL', 'https://test.api.com')
    monkeypatch.setenv('API_KEY', 'test_api_key')
    monkeypatch.setenv('DATABASE_URI', 'sqlite:///test.db')
    monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'test_access_key')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'test_secret_key')
    monkeypatch.setenv('AWS_REGION', 'us-west-2')
    
    config = Config()
    
    assert config.API_BASE_URL == 'https://test.api.com'
    assert config.API_KEY == 'test_api_key'
    assert config.DATABASE_URI == 'sqlite:///test.db'
    assert config.S3_BUCKET_NAME == 'test-bucket'
    assert config.AWS_ACCESS_KEY_ID == 'test_access_key'
    assert config.AWS_SECRET_ACCESS_KEY == 'test_secret_key'
    assert config.AWS_REGION == 'us-west-2'
