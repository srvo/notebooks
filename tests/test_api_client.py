import pytest
from unittest.mock import patch, Mock
from jupyter.api_client import APIClient
from config import Config

@patch('requests.get')
def test_fetch_data_success(mock_get):
    mock_response = Mock()
    mock_response.json.return_value = {'data': 'test'}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    client = APIClient()
    result = client.fetch_data('test_endpoint')
    
    assert result == {'data': 'test'}
    mock_get.assert_called_with(
        f"{Config.API_BASE_URL}/test_endpoint",
        headers={'Authorization': f'Bearer {Config.API_KEY}'},
        params=None
    )

@patch('requests.get')
def test_fetch_data_failure(mock_get):
    mock_get.side_effect = Exception("API Error")
    
    client = APIClient()
    with pytest.raises(Exception):
        client.fetch_data('test_endpoint')
