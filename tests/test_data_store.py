import pytest
from unittest.mock import patch, Mock
from jupyter.data_store import DataStore
from config import Config
from botocore.exceptions import NoCredentialsError

@pytest.fixture
def mock_data_store():
    with patch('boto3.client'), patch('sqlalchemy.create_engine'):
        return DataStore()

def test_save_to_db_success(mock_data_store):
    """Test successful database save."""
    mock_session = Mock()
    mock_data_store.Session.return_value = mock_session
    
    mock_data_store.save_to_db({'key': 'value'})
    
    mock_session.commit.assert_called_once()
    mock_session.close.assert_called_once()

def test_save_to_db_failure(mock_data_store):
    """Test database save failure."""
    mock_session = Mock()
    mock_session.commit.side_effect = Exception("DB Error")
    mock_data_store.Session.return_value = mock_session
    
    with pytest.raises(Exception):
        mock_data_store.save_to_db({'key': 'value'})
    mock_session.rollback.assert_called_once()

def test_backup_to_s3_success(mock_data_store):
    """Test successful S3 backup."""
    mock_data_store.backup_to_s3('test.db')
    
    mock_data_store.s3_client.upload_file.assert_called_with(
        'test.db',
        Config.S3_BUCKET_NAME,
        'test.db'
    )

def test_backup_to_s3_file_not_found(mock_data_store):
    """Test S3 backup with file not found."""
    mock_data_store.s3_client.upload_file.side_effect = FileNotFoundError
    with pytest.raises(FileNotFoundError):
        mock_data_store.backup_to_s3('test.db')

def test_backup_to_s3_no_credentials(mock_data_store):
    """Test S3 backup with missing credentials."""
    mock_data_store.s3_client.upload_file.side_effect = NoCredentialsError
    with pytest.raises(NoCredentialsError):
        mock_data_store.backup_to_s3('test.db')
