import pytest
from unittest.mock import Mock, patch
from jupyter.search_flow import SearchFlow
from jupyter.api_client import APIClient
from jupyter.data_store import DataStore
from jupyter.data_processor import DataProcessor

@pytest.fixture
def mock_components():
    return {
        'api_client': Mock(spec=APIClient),
        'data_store': Mock(spec=DataStore),
        'data_processor': Mock(spec=DataProcessor)
    }

def test_search_flow_fetch_data_success(mock_components):
    """Test successful data fetching."""
    mock_components['api_client'].fetch_data.return_value = {'data': 'test'}
    search_flow = SearchFlow(**mock_components)
    result = search_flow.fetch_data('test query')
    
    assert result == {'data': 'test'}
    mock_components['api_client'].fetch_data.assert_called_once_with('search_endpoint', params={'query': 'test query'})

def test_search_flow_fetch_data_failure(mock_components):
    """Test data fetching failure."""
    mock_components['api_client'].fetch_data.side_effect = Exception("API Error")
    search_flow = SearchFlow(**mock_components)
    
    with pytest.raises(Exception):
        search_flow.fetch_data('test query')

def test_search_flow_process_data_success(mock_components):
    """Test successful data processing."""
    mock_components['data_processor'].process.return_value = {'processed': True}
    search_flow = SearchFlow(**mock_components)
    result = search_flow.process_data({'data': 'test'})
    
    assert result == {'processed': True}
    mock_components['data_processor'].process.assert_called_once_with({'data': 'test'})

def test_search_flow_process_data_failure(mock_components):
    """Test data processing failure."""
    mock_components['data_processor'].process.side_effect = Exception("Processing Error")
    search_flow = SearchFlow(**mock_components)
    
    with pytest.raises(Exception):
        search_flow.process_data({'data': 'test'})

def test_search_flow_save_data_success(mock_components):
    """Test successful data saving."""
    search_flow = SearchFlow(**mock_components)
    search_flow.save_data({'processed': True})
    
    mock_components['data_store'].save_to_db.assert_called_once_with({'processed': True})
    mock_components['data_store'].backup_to_s3.assert_called_once_with('data/research.db')

def test_search_flow_save_data_failure(mock_components):
    """Test data saving failure."""
    mock_components['data_store'].save_to_db.side_effect = Exception("Save Error")
    search_flow = SearchFlow(**mock_components)
    
    with pytest.raises(Exception):
        search_flow.save_data({'processed': True})

def test_search_flow_process_search_success(mock_components):
    """Test successful search flow."""
    mock_components['api_client'].fetch_data.return_value = {'data': 'test'}
    mock_components['data_processor'].process.return_value = {'processed': True}
    search_flow = SearchFlow(**mock_components)
    search_flow.process_search('test query')
    
    mock_components['api_client'].fetch_data.assert_called_once()
    mock_components['data_processor'].process.assert_called_once()
    mock_components['data_store'].save_to_db.assert_called_once()
    mock_components['data_store'].backup_to_s3.assert_called_once()

def test_search_flow_process_search_failure(mock_components):
    """Test search flow failure."""
    mock_components['api_client'].fetch_data.side_effect = Exception("API Error")
    search_flow = SearchFlow(**mock_components)
    
    with pytest.raises(Exception):
        search_flow.process_search('test query')
