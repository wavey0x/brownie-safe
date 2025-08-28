import os
import pytest
import requests
from unittest.mock import Mock, patch, MagicMock
from brownie_safe import (
    SafeTransactionServiceConfig, 
    SafeTransactionServiceClient, 
    ApiError
)


class TestSafeTransactionServiceConfig:
    """Test configuration handling."""

    def test_default_config(self):
        """Test default configuration values."""
        with patch.dict(os.environ, {}, clear=True):
            config = SafeTransactionServiceConfig()
            assert config.api_key is None
            assert config.base_url == 'https://api.safe.global/tx-service'
            assert config.chain_override is None
            assert config.timeout == 20
            assert config.retries == 3
            assert config.allow_no_key is False

    def test_env_config(self):
        """Test configuration from environment variables."""
        env_vars = {
            'SAFE_TRANSACTION_SERVICE_API_KEY': 'test-key',
            'SAFE_TX_SERVICE_BASE': 'https://custom.api.com/tx-service',
            'SAFE_TX_SERVICE_CHAIN': 'custom',
            'SAFE_TX_TIMEOUT_SEC': '30',
            'SAFE_TX_RETRIES': '5',
            'SAFE_TX_ALLOW_NO_KEY': 'true',
        }
        
        with patch.dict(os.environ, env_vars):
            config = SafeTransactionServiceConfig()
            assert config.api_key == 'test-key'
            assert config.base_url == 'https://custom.api.com/tx-service'
            assert config.chain_override == 'custom'
            assert config.timeout == 30
            assert config.retries == 5
            assert config.allow_no_key is True

    def test_chain_code_mapping(self):
        """Test chain code resolution."""
        config = SafeTransactionServiceConfig()
        
        # Known chains
        assert config.get_chain_code(1) == 'eth'
        assert config.get_chain_code(10) == 'oeth'
        assert config.get_chain_code(8453) == 'base'
        assert config.get_chain_code(42161) == 'arb1'
        assert config.get_chain_code(100) == 'gno'
        assert config.get_chain_code(137) == 'matic'
        assert config.get_chain_code(56) == 'bnb'

    def test_unknown_chain_warning(self):
        """Test warning for unknown chain ID."""
        config = SafeTransactionServiceConfig()
        
        with pytest.warns(UserWarning, match="Unknown chain ID 999999"):
            chain_code = config.get_chain_code(999999)
            assert chain_code == 'eth'  # fallback

    def test_chain_override(self):
        """Test chain override functionality."""
        with patch.dict(os.environ, {'SAFE_TX_SERVICE_CHAIN': 'custom'}):
            config = SafeTransactionServiceConfig()
            assert config.get_chain_code(1) == 'custom'
            assert config.get_chain_code(999999) == 'custom'


class TestSafeTransactionServiceClient:
    """Test HTTP client functionality."""

    def test_client_initialization(self):
        """Test client initialization with API key."""
        with patch.dict(os.environ, {'SAFE_TRANSACTION_SERVICE_API_KEY': 'test-key'}):
            client = SafeTransactionServiceClient(1)
            assert client.chain_id == 1
            assert client.chain_code == 'eth'
            assert client.base_url == 'https://api.safe.global/tx-service/eth'

    def test_client_initialization_no_key(self):
        """Test client initialization fails without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ApiError, match="SAFE_TRANSACTION_SERVICE_API_KEY is required"):
                SafeTransactionServiceClient(1)

    def test_client_initialization_no_key_allowed(self):
        """Test client initialization succeeds with allow_no_key."""
        with patch.dict(os.environ, {'SAFE_TX_ALLOW_NO_KEY': 'true'}):
            client = SafeTransactionServiceClient(1)
            assert client.chain_id == 1

    def test_headers_with_api_key(self):
        """Test headers include authorization when API key is present."""
        with patch.dict(os.environ, {'SAFE_TRANSACTION_SERVICE_API_KEY': 'test-key'}):
            client = SafeTransactionServiceClient(1)
            headers = client._get_headers()
            
            assert headers['Accept'] == 'application/json'
            assert headers['User-Agent'] == 'brownie-safe/0.10.0'
            assert headers['Authorization'] == 'Bearer test-key'

    def test_headers_without_api_key(self):
        """Test headers without authorization when no API key."""
        with patch.dict(os.environ, {'SAFE_TX_ALLOW_NO_KEY': 'true'}):
            client = SafeTransactionServiceClient(1)
            headers = client._get_headers()
            
            assert headers['Accept'] == 'application/json'
            assert headers['User-Agent'] == 'brownie-safe/0.10.0'
            assert 'Authorization' not in headers

    @patch('brownie_safe.requests.request')
    def test_successful_request(self, mock_request):
        """Test successful HTTP request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': 'success'}
        mock_request.return_value = mock_response
        
        with patch.dict(os.environ, {'SAFE_TRANSACTION_SERVICE_API_KEY': 'test-key'}):
            client = SafeTransactionServiceClient(1)
            response = client.get('/test')
            
            assert response.status_code == 200
            mock_request.assert_called_once()
            args, kwargs = mock_request.call_args
            assert args[0] == 'GET'
            assert args[1] == 'https://api.safe.global/tx-service/eth/test'
            assert kwargs['headers']['Authorization'] == 'Bearer test-key'

    @patch('brownie_safe.requests.request')
    def test_401_error_handling(self, mock_request):
        """Test 401 unauthorized error handling."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_request.return_value = mock_response
        
        with patch.dict(os.environ, {'SAFE_TRANSACTION_SERVICE_API_KEY': 'bad-key'}):
            client = SafeTransactionServiceClient(1)
            
            with pytest.raises(ApiError, match="Unauthorized.*Check your SAFE_TRANSACTION_SERVICE_API_KEY"):
                client.get('/test')

    @patch('brownie_safe.requests.request')
    @patch('brownie_safe.time.sleep')
    def test_retry_logic(self, mock_sleep, mock_request):
        """Test retry logic for transient failures."""
        # First two calls return 429, third succeeds
        responses = [
            Mock(status_code=429),
            Mock(status_code=429),
            Mock(status_code=200)
        ]
        responses[2].json.return_value = {'result': 'success'}
        mock_request.side_effect = responses
        
        with patch.dict(os.environ, {'SAFE_TRANSACTION_SERVICE_API_KEY': 'test-key'}):
            client = SafeTransactionServiceClient(1)
            response = client.get('/test')
            
            assert response.status_code == 200
            assert mock_request.call_count == 3
            assert mock_sleep.call_count == 2  # Two retry delays

    @patch('brownie_safe.requests.request')
    def test_retry_exhaustion(self, mock_request):
        """Test behavior when retries are exhausted."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_request.return_value = mock_response
        
        with patch.dict(os.environ, {'SAFE_TRANSACTION_SERVICE_API_KEY': 'test-key', 'SAFE_TX_RETRIES': '2'}):
            client = SafeTransactionServiceClient(1)
            
            with pytest.raises(requests.exceptions.HTTPError):
                client.get('/test')
            
            assert mock_request.call_count == 3  # Initial + 2 retries

    @patch('brownie_safe.requests.request')
    def test_post_request(self, mock_request):
        """Test POST request functionality."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        with patch.dict(os.environ, {'SAFE_TRANSACTION_SERVICE_API_KEY': 'test-key'}):
            client = SafeTransactionServiceClient(1)
            test_data = {'key': 'value'}
            
            response = client.post('/test', json=test_data)
            
            assert response.status_code == 200
            mock_request.assert_called_once()
            args, kwargs = mock_request.call_args
            assert args[0] == 'POST'
            assert kwargs['json'] == test_data

    def test_custom_config(self):
        """Test client with custom configuration."""
        config = SafeTransactionServiceConfig()
        config.base_url = 'https://custom.api.com/tx-service'
        config.api_key = 'custom-key'
        
        client = SafeTransactionServiceClient(1, config)
        assert client.base_url == 'https://custom.api.com/tx-service/eth'
        
        headers = client._get_headers()
        assert headers['Authorization'] == 'Bearer custom-key'


class TestIntegration:
    """Integration tests for the full migration."""

    def test_version_import(self):
        """Test that all required classes can be imported."""
        from brownie_safe import (
            SafeTransactionServiceConfig,
            SafeTransactionServiceClient,
            BrownieSafe,
            ApiError
        )
        assert SafeTransactionServiceConfig is not None
        assert SafeTransactionServiceClient is not None
        assert BrownieSafe is not None
        assert ApiError is not None

    def test_backwards_compatibility_warning(self):
        """Test that base_url parameter shows deprecation warning."""
        with patch('brownie_safe.to_address') as mock_to_address, \
             patch('brownie_safe.EthereumClient') as mock_client, \
             patch('brownie_safe.Safe') as mock_safe, \
             patch('brownie_safe.TransactionServiceApi') as mock_ts_api, \
             patch('brownie_safe.MultiSend') as mock_multisend, \
             patch('brownie_safe.chain') as mock_chain:
            
            mock_to_address.return_value = '0x1234'
            mock_safe.return_value.get_version.return_value = '1.3.0'
            mock_chain.id = 1
            
            with pytest.warns(DeprecationWarning, match="base_url parameter is deprecated"):
                from brownie_safe import BrownieSafe
                BrownieSafe('0x1234', base_url='https://custom.api.com')