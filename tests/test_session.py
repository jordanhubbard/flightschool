import pytest
from flask import session
from flask_login import current_user
from app.models import User
from app import db

def test_user_session(client, test_user, app):
    """Test that a user can be properly attached to a session."""
    with app.app_context():
        # Verify the user exists in the database
        user = User.query.filter_by(email='test@example.com').first()
        assert user is not None
        assert user.id == test_user.id
        
        # Get CSRF token
        response = client.get('/auth/login')
        html = response.data.decode()
        csrf_token = html.split('name="csrf_token" type="hidden" value="')[1].split('"')[0]
        
        # Test login
        response = client.post(
            '/auth/login',
            data={
                'email': 'test@example.com',
                'password': 'test123',
                'csrf_token': csrf_token
            },
            follow_redirects=True
        )
        assert response.status_code == 200
        assert current_user.is_authenticated
        assert current_user.id == test_user.id
        
        # Test accessing a protected route
        response = client.get('/booking/dashboard')
        assert response.status_code == 200
        assert b'My Schedule' in response.data

def test_session_persistence(client, test_user, app):
    """Test that session data persists across requests."""
    with app.app_context():
        # Get CSRF token
        response = client.get('/auth/login')
        html = response.data.decode()
        csrf_token = html.split('name="csrf_token" type="hidden" value="')[1].split('"')[0]
        
        # Login
        response = client.post(
            '/auth/login',
            data={
                'email': 'test@example.com',
                'password': 'test123',
                'csrf_token': csrf_token
            },
            follow_redirects=True
        )
        assert response.status_code == 200
        assert current_user.is_authenticated
        
        # Make multiple requests and verify session persists
        for _ in range(3):
            response = client.get('/booking/dashboard')
            assert response.status_code == 200
            assert current_user.is_authenticated
            assert current_user.id == test_user.id

def test_session_clear_on_logout(client, test_user, app):
    """Test that session data is cleared on logout."""
    with app.app_context():
        # Get CSRF token
        response = client.get('/auth/login')
        html = response.data.decode()
        csrf_token = html.split('name="csrf_token" type="hidden" value="')[1].split('"')[0]
        
        # Login
        response = client.post(
            '/auth/login',
            data={
                'email': 'test@example.com',
                'password': 'test123',
                'csrf_token': csrf_token
            },
            follow_redirects=True
        )
        assert response.status_code == 200
        assert current_user.is_authenticated
        
        # Logout
        response = client.get('/auth/logout', follow_redirects=True)
        assert response.status_code == 200
        assert not current_user.is_authenticated
        
        # Verify session is cleared
        assert 'user_id' not in session
        
        # Verify protected routes are no longer accessible
        response = client.get('/booking/dashboard', follow_redirects=True)
        assert b'Please log in to access this page.' in response.data 