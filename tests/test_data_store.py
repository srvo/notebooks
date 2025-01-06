import pytest
from unittest.mock import patch, Mock
from jupyter.data_store import DataStore
from config import Config

@patch('boto3.client')
@patch('sqlalchemy.create_engine')
def test_save_to_db_success(mock_engine, mock_s3):
    mock_session = Mock()
    mock_engine.return_value = Mock()
    mock_engine.return_value.sessionmaker.return_value.return_value = mock_session
    
    store = DataStore()
    test_data = {'key': 'value'}
    store.save_to_db(test_data)
    
    mock_session.commit.assert_called_once()
    mock_session.close.assert_called_once()

@patch('boto3.client')
def test_backup_to_s3_success(mock_s3):
    mock_client = Mock()
    mock_s3.return_value = mock_client
    
    store = DataStore()
    store.backup_to_s3('test.db')
    
    mock_client.upload_file.assert_called_with(
        'test.db',
        Config.S3_BUCKET_NAME,
        'test.db'
    )
