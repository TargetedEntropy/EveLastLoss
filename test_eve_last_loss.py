import pytest
import datetime
from unittest.mock import patch, MagicMock
from dateutil import parser

# Import your class - adjust the import path as needed
from eve_last_loss import EveOnlineAPI


@pytest.fixture
def mock_api():
    """Create a mock EveOnlineAPI instance with test data."""
    with patch('eve_last_loss.requests.get') as mock_get:
        api = EveOnlineAPI('fake_token', '12345')
        # Add the mock_get to the api so tests can configure it
        api.mock_get = mock_get
        yield api


class TestEveOnlineAPI:
    
    def test_initialization(self):
        """Test that the API class initializes correctly."""
        api = EveOnlineAPI('test_token', '12345')
        
        assert api.access_token == 'test_token'
        assert api.character_id == 12345
        assert api.headers == {
            "Authorization": "Bearer test_token",
            "Content-Type": "application/json"
        }
    
    def test_make_request_success(self, mock_api):
        """Test successful API requests."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "test_data"}
        mock_api.mock_get.return_value = mock_response
        
        # Test the method
        result = mock_api._make_request('/test/endpoint')
        
        # Assertions
        assert result == {"data": "test_data"}
        mock_api.mock_get.assert_called_once_with(
            f"{EveOnlineAPI.BASE_URL}/test/endpoint", 
            headers=mock_api.headers, 
            params=None
        )
    
   
    def test_get_recent_killmails(self, mock_api):
        """Test retrieving recent killmails."""
        # Setup mock data
        mock_killmails = [{"killmail_id": 123, "killmail_hash": "abc123"}]
        mock_response = MagicMock()
        mock_response.json.return_value = mock_killmails
        mock_api.mock_get.return_value = mock_response
        
        # Test the method
        result = mock_api.get_recent_killmails()
        
        # Assertions
        assert result == mock_killmails
        mock_api.mock_get.assert_called_once_with(
            f"{EveOnlineAPI.BASE_URL}/characters/12345/killmails/recent/",
            headers=mock_api.headers,
            params=None
        )
    
    def test_get_killmail_details(self, mock_api):
        """Test retrieving specific killmail details."""
        # Setup mock data
        kill_id = 123
        kill_hash = "abc123"
        mock_details = {"victim": {"character_id": 12345}}
        mock_response = MagicMock()
        mock_response.json.return_value = mock_details
        mock_api.mock_get.return_value = mock_response
        
        # Test the method
        result = mock_api.get_killmail_details(kill_id, kill_hash)
        
        # Assertions
        assert result == mock_details
        mock_api.mock_get.assert_called_once_with(
            f"{EveOnlineAPI.BASE_URL}/killmails/{kill_id}/{kill_hash}/",
            headers=mock_api.headers,
            params=None
        )
    
    def test_get_ship_info(self, mock_api):
        """Test retrieving ship information."""
        # Setup mock data
        ship_type_id = 456
        mock_ship_info = {"name": "Test Ship"}
        mock_response = MagicMock()
        mock_response.json.return_value = mock_ship_info
        mock_api.mock_get.return_value = mock_response
        
        # Test the method
        result = mock_api.get_ship_info(ship_type_id)
        
        # Assertions
        assert result == mock_ship_info
        mock_api.mock_get.assert_called_once_with(
            f"{EveOnlineAPI.BASE_URL}/universe/types/{ship_type_id}/",
            headers=mock_api.headers,
            params=None
        )
    
    def test_filter_character_losses(self, mock_api):
        """Test filtering killmails for character losses."""
        # Setup mock data and behavior for get_killmail_details
        killmails = [
            {"killmail_id": 123, "killmail_hash": "abc123"},
            {"killmail_id": 456, "killmail_hash": "def456"}
        ]
        
        def mock_get_details(kill_id, kill_hash):
            if kill_id == 123:
                return {"victim": {"character_id": 12345}}  # This is our character
            else:
                return {"victim": {"character_id": 67890}}  # This is someone else
        
        # Use patch to mock the get_killmail_details method
        with patch.object(mock_api, 'get_killmail_details', side_effect=mock_get_details):
            result = mock_api.filter_character_losses(killmails)
        
        # Assertions
        assert len(result) == 1
        assert result[0]["victim"]["character_id"] == 12345
    
    def test_find_most_recent_loss_empty(self):
        """Test finding most recent loss with empty list."""
        api = EveOnlineAPI('test_token', '12345')
        result = api.find_most_recent_loss([])
        assert result is None
    
    def test_find_most_recent_loss(self):
        """Test finding most recent loss from multiple losses."""
        api = EveOnlineAPI('test_token', '12345')
        
        # Create test data with different timestamps
        older_loss = {"killmail_time": "2023-01-01T12:00:00Z"}
        newer_loss = {"killmail_time": "2023-01-02T12:00:00Z"}
        newest_loss = {"killmail_time": "2023-01-03T12:00:00Z"}
        
        losses = [older_loss, newest_loss, newer_loss]
        
        result = api.find_most_recent_loss(losses)
        assert result == newest_loss
    
    def test_format_time_difference(self):
        """Test formatting time difference."""
        api = EveOnlineAPI('test_token', '12345')
        
        # Create a timedelta for testing
        time_diff = datetime.timedelta(days=2, hours=3, minutes=45, seconds=30)
        
        result = api.format_time_difference(time_diff)
        
        assert "2 days" in result
        assert "3 hours" in result
        assert "45 minutes" in result
        assert "30 seconds" in result
    
    @patch('eve_last_loss.datetime')
    def test_get_time_since_last_ship_loss_success(self, mock_datetime, mock_api):
        """Test the full flow of getting time since last ship loss."""
        # Setup current time
        mock_now = datetime.datetime(2023, 1, 10, 12, 0, 0, tzinfo=datetime.timezone.utc)
        mock_datetime.datetime.now.return_value = mock_now
        
        # Setup mock data for various method calls
        killmails = [{"killmail_id": 123, "killmail_hash": "abc123"}]
        
        loss_time_str = "2023-01-05T12:00:00Z"
        loss_detail = {
            "victim": {
                "character_id": 12345,
                "ship_type_id": 456
            },
            "killmail_time": loss_time_str
        }
        
        ship_info = {"name": "Test Ship"}
        
        # Mock the methods that would make API calls
        with patch.object(mock_api, 'get_recent_killmails', return_value=killmails), \
             patch.object(mock_api, 'filter_character_losses', return_value=[loss_detail]), \
             patch.object(mock_api, 'find_most_recent_loss', return_value=loss_detail), \
             patch.object(mock_api, 'get_ship_info', return_value=ship_info):
            
            result = mock_api.get_time_since_last_ship_loss()
        
        # Assertions
        assert "Time since last ship loss:" in result
        assert "5 days" in result  # Time diff between Jan 5 and Jan 10
        assert "Lost ship: Test Ship" in result
    
    def test_get_time_since_last_ship_loss_no_losses(self, mock_api):
        """Test handling no ship losses found."""
        # Mock the methods to return no losses
        with patch.object(mock_api, 'get_recent_killmails', return_value=[]), \
             patch.object(mock_api, 'filter_character_losses', return_value=[]):
            
            result = mock_api.get_time_since_last_ship_loss()
        
        # Assertions
        assert result == "No ship losses found for this character."
    
    def test_get_time_since_last_ship_loss_error(self, mock_api):
        """Test handling unexpected errors."""
        # Mock the first method to raise an exception
        with patch.object(mock_api, 'get_recent_killmails', side_effect=Exception("Test error")):
            result = mock_api.get_time_since_last_ship_loss()
        
        # Assertions
        assert "An unexpected error occurred: Test error" in result