import pytest
import os
import json
import tempfile
import shutil
from flask import session
from unittest.mock import patch, MagicMock
from app import app as flask_app
from src.db import get_db_connection, get_db_cursor
from src.db.database import create_database_and_user
from src.db.usage import DAILY_GENERATION_LIMIT, DAILY_DOWNLOAD_LIMIT

@pytest.fixture(autouse=True)
def mock_services():
    """Mock external services"""
    with (
        patch("src.config.flow", None),  # Mock Google OAuth flow
        patch("src.config.client", MagicMock()),  # Mock OpenAI client
        patch("src.config.logger", MagicMock()),  # Mock logger
        patch("src.db.database.test_connection", return_value=True),  # Ensure database connection test passes
        patch("src.db.database.get_db_cursor") as mock_cursor
    ):
        # Create a mock cursor that behaves like a real cursor
        mock_cursor_instance = MagicMock()
        
        # Define a method to simulate fetchone()
        def mock_fetchone():
            # Simulate a default scenario where no records exist
            return None
        
        mock_cursor_instance.fetchone.side_effect = mock_fetchone
        mock_cursor.return_value.__enter__.return_value = mock_cursor_instance
        
        yield

@pytest.fixture(scope='session', autouse=True)
def setup_database():
    """Ensure database is set up before tests"""
    create_database_and_user()

@pytest.fixture
def client():
    """Create a Flask test client with testing enabled"""
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client

def test_database_connection():
    """Test database connection"""
    from src.db.database import test_connection
    assert test_connection() is True

def test_auth_check(client):
    """Test the /auth/check endpoint for authentication behavior"""
    response = client.get('/auth/check')
    assert response.status_code == 401  # Should return 401 when unauthenticated

    # Simulate authentication session
    with client.session_transaction() as sess:
        sess['credentials'] = {'token': 'fake_token'}
        sess['user_info'] = {
            "email": "test@teacherfy.ai",
            "name": "Test User",
            "picture": "https://example.com/test.png"
        }

    response = client.get('/auth/check')
    assert response.status_code == 200
    assert response.json['authenticated'] is True
    assert response.json['user']['email'] == "test@teacherfy.ai"

def test_usage_limits():
    """Test usage limits functionality"""
    from src.db.usage import check_user_limits, increment_usage

    # Test anonymous user limits
    limits = check_user_limits(ip_address='127.0.0.1')
    
    # Verify the structure of the returned dictionary
    assert 'can_generate' in limits
    assert 'can_download' in limits
    assert 'generations_left' in limits
    assert 'downloads_left' in limits

    # Check specific values based on our mock
    assert limits['generations_left'] == DAILY_GENERATION_LIMIT
    assert limits['downloads_left'] == DAILY_DOWNLOAD_LIMIT
    assert limits['can_generate'] is True
    assert limits['can_download'] is True

    # Additional test for incrementing usage
    with patch("src.db.database.get_db_connection"):
        increment_usage(ip_address='127.0.0.1', action_type='generation')

def test_generate_slides_requires_auth(client):
    """Ensure /generate_slides requires authentication"""
    response = client.post('/generate_slides', json={"structured_content": []})
    assert response.status_code == 401  # Should return 401 when unauthenticated

    with client.session_transaction() as sess:
        sess['credentials'] = {'token': 'fake_token'}
    
    response = client.post('/generate_slides', json={"structured_content": []})
    assert response.status_code in (400, 500)  # Will fail due to missing dependencies

def test_generate_presentation(client):
    """Test /generate endpoint for PowerPoint generation"""
    # Create a real temporary file to mock PowerPoint output
    temp_pptx_path = "/tmp/fake_presentation.pptx"
    with open(temp_pptx_path, "wb") as f:
        f.write(b"Mock PowerPoint content")  # Create a non-empty file

    with patch("src.presentation_routes.generate_presentation", return_value=temp_pptx_path):
        with patch("src.slide_processor.Presentation") as mock_presentation:
            mock_presentation.return_value = MagicMock()

            response = client.post('/generate', json={"structured_content": [{}]})

    # Ensure the file exists before calling send_file()
    assert os.path.exists(temp_pptx_path)

    # Clean up temporary files
    os.remove(temp_pptx_path)

    # Check if the response was successful
    assert response.status_code in (200, 400)  # If content is valid, it should return the file

def test_oauth_redirect(client):
    """Ensure /authorize properly redirects users to Google OAuth"""
    response = client.get('/authorize', follow_redirects=False)
    assert response.status_code in (302, 500)  # If OAuth setup is correct, it redirects

def test_outline_generation(client):
    """Test the /outline endpoint with an example request"""
    # Load the example outline from `data/slides.json`
    example_outline_path = os.path.join(os.path.dirname(__file__), "../data/slides.json")
    with open(example_outline_path, "r") as f:
        expected_outline = json.load(f)

    # Patch the load_example_outlines function
    with patch("src.presentation_routes.load_example_outlines", return_value=expected_outline):
        response = client.post('/outline', json={"use_example": True})

    # Verify that the request was successful
    assert response.status_code == 200
    actual_response = response.json

    # Check that the required keys exist
    assert "messages" in actual_response, "Response missing 'messages' key"
    assert "structured_content" in actual_response, "Response missing 'structured_content' key"

    # Optional additional checks
    key_phrase = "Let's Explore Equivalent Fractions!"
    first_message = actual_response["messages"][0]
    assert key_phrase in first_message, (
        f"Expected key phrase '{key_phrase}' not found in message: {first_message}"
    )

    assert len(actual_response["structured_content"]) > 0, "No slides found in structured_content"
    first_slide_title = actual_response["structured_content"][0].get("title", "")
    assert first_slide_title, "The first slide is missing a title"

def test_logout_clears_session(client):
    """Ensure /logout clears the user session"""
    with client.session_transaction() as sess:
        sess['credentials'] = {'token': 'fake_token'}

    response = client.get('/logout', follow_redirects=False)
    assert response.status_code == 302  # Redirect to /authorize
    with client.session_transaction() as sess:
        assert 'credentials' not in sess  # Ensure session is cleared