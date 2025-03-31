import pytest
from flask import session
from flask_login import current_user
from app.models import User
from app import db

def test_login(client, test_user, app):
    """Test login functionality."""
    with app.app_context():
        # Get CSRF token
        response = client.get('/auth/login')
        html = response.data.decode()
        csrf_token = html.split('name="csrf_token" type="hidden" value="')[1].split('"')[0]
        
        # Test login
        response = client.post(
            '/auth/login',
            data={
                'email': 'test@example.com',
                'password': 'password123',
                'csrf_token': csrf_token
            },
            follow_redirects=True
        )
        assert response.status_code == 200
        assert b'Welcome to Eyes Outside Aviation' in response.data
        assert b'My Schedule' in response.data
        assert current_user.is_authenticated
        assert current_user.email == 'test@example.com'

def test_login_invalid_credentials(client, test_user, app):
    """Test login with invalid credentials."""
    with app.app_context():
        # Get CSRF token
        response = client.get('/auth/login')
        html = response.data.decode()
        csrf_token = html.split('name="csrf_token" type="hidden" value="')[1].split('"')[0]
        
        response = client.post(
            '/auth/login',
            data={
                'email': 'test@example.com',
                'password': 'wrongpass',
                'csrf_token': csrf_token
            },
            follow_redirects=True
        )
        assert response.status_code == 200
        assert b'Invalid email or password' in response.data
        assert not current_user.is_authenticated

def test_login_inactive_user(client, test_user, app):
    """Test login with inactive user account."""
    with app.app_context():
        # Get user from database and set as inactive
        user = User.query.filter_by(email='test@example.com').first()
        user.status = 'inactive'
        db.session.commit()
        db.session.refresh(user)
        
        # Get CSRF token
        response = client.get('/auth/login')
        html = response.data.decode()
        csrf_token = html.split('name="csrf_token" type="hidden" value="')[1].split('"')[0]
        
        response = client.post(
            '/auth/login',
            data={
                'email': 'test@example.com',
                'password': 'password123',
                'csrf_token': csrf_token
            },
            follow_redirects=True
        )
        assert response.status_code == 200
        assert b'Your account is not active. Please contact an administrator.' in response.data
        assert not current_user.is_authenticated

def test_logout(client, logged_in_user, app):
    """Test logout functionality."""
    with app.app_context():
        # Verify user is logged in
        response = client.get('/')
        assert current_user.is_authenticated
        assert current_user.email == 'test@example.com'
        
        # Test logout
        response = client.get('/auth/logout', follow_redirects=True)
        assert response.status_code == 200
        assert b'You have been logged out' in response.data
        assert not current_user.is_authenticated

def test_login_required(client, app):
    """Test that protected routes require login."""
    with app.app_context():
        # Try to access protected route without login
        response = client.get('/booking/dashboard', follow_redirects=True)
        assert response.status_code == 200
        assert b'Please log in to access this page.' in response.data

def test_remember_me(client, test_user, app):
    """Test remember me functionality."""
    with app.app_context():
        # Get CSRF token
        response = client.get('/auth/login')
        html = response.data.decode()
        csrf_token = html.split('name="csrf_token" type="hidden" value="')[1].split('"')[0]
        
        # Test login with remember me
        response = client.post(
            '/auth/login',
            data={
                'email': 'test@example.com',
                'password': 'password123',
                'remember': True,
                'csrf_token': csrf_token
            },
            follow_redirects=True
        )
        assert response.status_code == 200
        assert current_user.is_authenticated
        assert session.permanent
