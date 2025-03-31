import pytest
from flask import session
from flask_login import current_user
from app.models import User
from app import db

def test_login(client, test_user, _db):
    """Test user login."""
    response = client.post('/auth/login', data={
        'email': test_user.email,
        'password': 'password123',
        'remember_me': False
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Welcome back' in response.data
    assert session.get('user_id') == test_user.id

def test_login_invalid_credentials(client, test_user, _db):
    """Test login with invalid credentials."""
    response = client.post('/auth/login', data={
        'email': test_user.email,
        'password': 'wrongpassword',
        'remember_me': False
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Invalid email or password' in response.data
    assert session.get('user_id') is None

def test_login_inactive_user(client, test_user, _db):
    """Test login with inactive user."""
    test_user.is_active = False
    _db.session.commit()
    
    response = client.post('/auth/login', data={
        'email': test_user.email,
        'password': 'password123',
        'remember_me': False
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Your account is inactive' in response.data
    assert session.get('user_id') is None

def test_logout(client, test_user, _db):
    """Test user logout."""
    with client.session_transaction() as sess:
        sess['user_id'] = test_user.id
        sess['_fresh'] = True
    
    response = client.get('/auth/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'You have been logged out' in response.data
    assert session.get('user_id') is None

def test_login_required(client):
    """Test login required decorator."""
    response = client.get('/booking/dashboard', follow_redirects=True)
    assert response.status_code == 200
    assert b'Please log in to access this page' in response.data

def test_remember_me(client, test_user, _db):
    """Test remember me functionality."""
    response = client.post('/auth/login', data={
        'email': test_user.email,
        'password': 'password123',
        'remember_me': True
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Welcome back' in response.data
    assert session.get('user_id') == test_user.id
    assert session.get('_fresh') is True
