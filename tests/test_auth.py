import pytest
from flask import session
from flask_login import current_user
from app.models import User
from app import db

def test_login(client, test_user, session):
    """Test user login."""
    response = client.post('/login', data={
        'email': test_user.email,
        'password': 'password123',
        'remember_me': False
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Booking Dashboard' in response.data

def test_login_invalid_credentials(client, test_user, session):
    """Test login with invalid credentials."""
    response = client.post('/login', data={
        'email': test_user.email,
        'password': 'wrongpassword',
        'remember_me': False
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Invalid email or password' in response.data
    with client.session_transaction() as sess:
        assert sess.get('_user_id') is None

def test_login_inactive_user(client, test_user, session):
    """Test login with inactive user."""
    test_user.status = 'inactive'
    db.session.commit()
    
    response = client.post('/login', data={
        'email': test_user.email,
        'password': 'password123',
        'remember_me': False
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Your account is not active' in response.data
    with client.session_transaction() as sess:
        assert sess.get('_user_id') is None

def test_logout(client, test_user, session):
    """Test user logout."""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_user.id
        sess['_fresh'] = True
    
    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'You have been logged out' in response.data
    with client.session_transaction() as sess:
        assert sess.get('_user_id') is None

def test_login_required(client):
    """Test login required decorator."""
    response = client.get('/dashboard', follow_redirects=True)
    assert response.status_code == 200
    assert b'Sign In' in response.data

def test_remember_me(client, test_user, session):
    """Test remember me functionality."""
    response = client.post('/login', data={
        'email': test_user.email,
        'password': 'password123',
        'remember_me': True
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Booking Dashboard' in response.data
    with client.session_transaction() as sess:
        assert sess.get('_remember') == '1'

def test_admin_login_redirect(client, test_admin, session):
    """Test admin login redirect."""
    response = client.post('/login', data={
        'email': test_admin.email,
        'password': 'password123',
        'remember_me': False
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Admin Dashboard' in response.data

def test_student_login_redirect(client, test_student, session):
    """Test student login redirect."""
    response = client.post('/login', data={
        'email': test_student.email,
        'password': 'password123',
        'remember_me': False
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Booking Dashboard' in response.data
