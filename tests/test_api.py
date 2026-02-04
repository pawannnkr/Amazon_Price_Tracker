"""
Unit tests for API endpoints.
Tests API routes using Flask test client with PostgreSQL test database.
"""
import pytest
import json


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check returns healthy status."""
        response = client.get('/api/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'message' in data


class TestUsersAPI:
    """Tests for Users API endpoints."""
    
    def test_create_user(self, client, api_headers):
        """Test creating a new user."""
        response = client.post(
            '/api/users',
            data=json.dumps({
                'email': 'api_test@example.com',
                'name': 'API Test User'
            }),
            headers=api_headers
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['user']['email'] == 'api_test@example.com'
        assert data['user']['name'] == 'API Test User'
        assert 'id' in data['user']
    
    def test_create_user_missing_email(self, client, api_headers):
        """Test creating user without email fails."""
        response = client.post(
            '/api/users',
            data=json.dumps({'name': 'No Email User'}),
            headers=api_headers
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'email' in data['error'].lower()
    
    def test_create_user_invalid_email(self, client, api_headers):
        """Test creating user with invalid email format."""
        response = client.post(
            '/api/users',
            data=json.dumps({'email': 'not-an-email'}),
            headers=api_headers
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'invalid email' in data['error'].lower()
    
    def test_create_duplicate_user(self, client, api_headers):
        """Test creating user with duplicate email fails."""
        # Create first user
        response1 = client.post(
            '/api/users',
            data=json.dumps({'email': 'duplicate@example.com'}),
            headers=api_headers
        )
        assert response1.status_code == 201
        
        # Try to create duplicate
        response2 = client.post(
            '/api/users',
            data=json.dumps({'email': 'duplicate@example.com'}),
            headers=api_headers
        )
        
        assert response2.status_code == 409
        data = json.loads(response2.data)
        assert data['success'] is False
        assert 'already exists' in data['error'].lower()
    
    def test_list_users(self, client, api_headers):
        """Test listing all users."""
        response = client.get('/api/users', headers=api_headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'users' in data
        assert isinstance(data['users'], list)
    
    def test_get_user(self, client, api_headers):
        """Test getting a specific user."""
        # Create a user first
        create_response = client.post(
            '/api/users',
            data=json.dumps({'email': 'get_test@example.com'}),
            headers=api_headers
        )
        user_id = json.loads(create_response.data)['user']['id']
        
        # Get the user
        response = client.get(f'/api/users/{user_id}', headers=api_headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['user']['id'] == user_id
        assert data['user']['email'] == 'get_test@example.com'
    
    def test_get_nonexistent_user(self, client, api_headers):
        """Test getting a user that doesn't exist."""
        response = client.get('/api/users/99999', headers=api_headers)
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'not found' in data['error'].lower()
    
    def test_delete_user(self, client, api_headers):
        """Test deleting a user."""
        # Create a user
        create_response = client.post(
            '/api/users',
            data=json.dumps({'email': 'delete_test@example.com'}),
            headers=api_headers
        )
        user_id = json.loads(create_response.data)['user']['id']
        
        # Delete the user
        response = client.delete(f'/api/users/{user_id}', headers=api_headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Verify user is deleted
        get_response = client.get(f'/api/users/{user_id}', headers=api_headers)
        assert get_response.status_code == 404


class TestProductsAPI:
    """Tests for Products API endpoints."""
    
    def test_get_products_missing_user_id(self, client, api_headers):
        """Test getting products without user_id fails."""
        response = client.get('/api/products', headers=api_headers)
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'user_id' in data['error'].lower()
    
    def test_add_product_missing_url(self, client, api_headers):
        """Test adding product without URL fails."""
        response = client.post(
            '/api/products?user_id=1',
            data=json.dumps({'threshold': 5000.0}),
            headers=api_headers
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'url' in str(data).lower()
    
    def test_add_product_missing_threshold(self, client, api_headers, sample_user):
        """Test adding product without threshold fails."""
        response = client.post(
            f'/api/products?user_id={sample_user.id}',
            data=json.dumps({
                'url': 'https://www.amazon.in/dp/B0000000005'
            }),
            headers=api_headers
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_add_product_invalid_url(self, client, api_headers, sample_user):
        """Test adding product with invalid URL fails."""
        response = client.post(
            f'/api/products?user_id={sample_user.id}',
            data=json.dumps({
                'url': 'https://invalid-site.com/product',
                'threshold': 5000.0
            }),
            headers=api_headers
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'amazon' in data['error'].lower()
    
    def test_add_product_invalid_json(self, client, api_headers, sample_user):
        """Test adding product with non-JSON request fails."""
        response = client.post(
            f'/api/products?user_id={sample_user.id}',
            data='not json',
            headers=api_headers
        )
        
        assert response.status_code == 400


class TestNotificationsAPI:
    """Tests for Notifications API endpoints."""
    
    def test_get_notifications_missing_user_id(self, client, api_headers):
        """Test getting notifications without user_id fails."""
        response = client.get('/api/notifications', headers=api_headers)
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'user_id' in data['error'].lower()
    
    def test_update_notifications(self, client, api_headers, sample_user):
        """Test updating notification settings."""
        response = client.put(
            f'/api/notifications?user_id={sample_user.id}',
            data=json.dumps({
                'email': 'notify_test@example.com',
                'phone_number': '+919876543210'
            }),
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['notifications']['email'] == 'notify_test@example.com'


class TestHistoryAPI:
    """Tests for Price History API endpoints."""
    
    def test_get_history_missing_user_id(self, client, api_headers):
        """Test getting history without user_id fails."""
        response = client.get('/api/history', headers=api_headers)
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'user_id' in data['error'].lower()
    
    def test_get_history_by_id_missing_params(self, client, api_headers):
        """Test getting history by id without required params."""
        response = client.get('/api/history/by-id', headers=api_headers)
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False


class TestAPIValidation:
    """Tests for API input validation."""
    
    def test_json_content_type_required(self, client, sample_user):
        """Test that JSON content type is required for POST requests."""
        response = client.post(
            f'/api/products?user_id={sample_user.id}',
            data='not json',
            content_type='text/plain'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'json' in data['error'].lower()
    
    def test_url_validation_short_links(self, client, api_headers, sample_user):
        """Test that Amazon short links (amzn.in) are accepted."""
        response = client.post(
            f'/api/products?user_id={sample_user.id}',
            data=json.dumps({
                'url': 'https://amzn.in/someproduct',
                'threshold': 1000.0
            }),
            headers=api_headers
        )
        
        # Should not fail with "Invalid URL" error
        assert response.status_code != 400 or 'Invalid URL' not in json.loads(response.data).get('error', '')

