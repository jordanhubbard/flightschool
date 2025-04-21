import pytest
from flask import session
from flask_login import current_user
from app.models import User
from app import db

def test_login(client, test_user, session):
    """Test user login."""
    response = client.post('/auth/login', data={
        'email': test_user.email,
        'password': 'password123',
        'remember_me': False
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Flight Schedule' in response.data

def test_login_invalid_credentials(client, test_user, session):
    """Test login with invalid credentials."""
    response = client.post('/auth/login', data={
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

    response = client.post('/auth/login', data={
        'email': test_user.email,
        'password': 'password123',
        'remember_me': False
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Your account is not active' in response.data
    with client.session_transaction() as sess:
        assert sess.get('_user_id') is None

def test_admin_login_redirect(client, admin_user, session):
    """Test admin login redirect."""
    response = client.post('/auth/login', data={
        'email': admin_user.email,
        'password': 'password123',
        'remember_me': False
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Admin Dashboard' in response.data

def test_student_login_redirect(client, test_user, session):
    """Test student login redirect."""
    response = client.post('/auth/login', data={
        'email': test_user.email,
        'password': 'password123',
        'remember_me': False
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Flight Schedule' in response.data

def test_logout(client, test_user, session):
    """Test user logout."""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_user.id
        sess['_fresh'] = True

    response = client.get('/auth/logout', follow_redirects=True)
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
    response = client.post('/auth/login', data={
        'email': test_user.email,
        'password': 'password123',
        'remember_me': True
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Flight Schedule' in response.data
    with client.session_transaction() as sess:
        assert sess.get('_remember') == '1'

def test_register(client):
    """Test user registration."""
    response = client.post('/auth/register', data={
        'email': 'newuser@example.com',
        'password': 'password123',
        'first_name': 'New',
        'last_name': 'User',
        'phone': '555-0123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Registration successful' in response.data
    
    # Verify user was created
    user = User.query.filter_by(email='newuser@example.com').first()
    assert user is not None
    assert user.status == 'pending'

def test_change_password(client, test_user, session):
    """Test password change."""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_user.id
        sess['_fresh'] = True

    response = client.post('/auth/change-password', data={
        'current_password': 'password123',
        'new_password': 'newpassword123',
        'confirm_password': 'newpassword123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Password changed successfully' in response.data

    # Verify password was changed
    user = User.query.get(test_user.id)
    assert user.check_password('newpassword123')

def test_update_profile(client, test_user, session):
    """Test profile update."""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_user.id
        sess['_fresh'] = True

    response = client.post('/auth/update-profile', data={
        'first_name': 'Updated',
        'last_name': 'Name',
        'phone': '555-9999',
        'address': '123 Main St'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Profile updated successfully' in response.data

    # Verify profile was updated
    user = User.query.get(test_user.id)
    assert user.first_name == 'Updated'
    assert user.last_name == 'Name'
    assert user.phone == '555-9999'
    assert user.address == '123 Main St'
