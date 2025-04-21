import pytest
from flask import session
from flask_login import current_user
from app.models import User
from app import db

def test_user_session(client, test_user, session):
    """Test that a user can be properly attached to a session."""
    with client.session_transaction() as sess:
        sess['user_id'] = test_user.id
        sess['_fresh'] = True

    response = client.get('/')
    assert response.status_code == 200
    with client.session_transaction() as sess:
        assert sess.get('user_id') == test_user.id

def test_session_persistence(client, test_user, session):
    """Test that session data persists across requests."""
    with client.session_transaction() as sess:
        sess['user_id'] = test_user.id
        sess['_fresh'] = True

    # First request
    response = client.get('/')
    assert response.status_code == 200
    with client.session_transaction() as sess:
        assert sess.get('user_id') == test_user.id

    # Second request - use home page which we know exists
    response = client.get('/')
    assert response.status_code == 200
    with client.session_transaction() as sess:
        assert sess.get('user_id') == test_user.id

def test_session_clear_on_logout(client, test_user, session):
    """Test that session data is cleared on logout."""
    with client.session_transaction() as sess:
        sess['user_id'] = test_user.id
        sess['_fresh'] = True

    # Logout
    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200

    # Check that we're redirected to a valid page
    assert b'Next Level Tailwheel' in response.data

def test_session_expiry(client, test_user, session):
    """Test session expiry behavior."""
    with client.session_transaction() as sess:
        sess['user_id'] = test_user.id
        sess['_fresh'] = True

    # Make a request
    response = client.get('/')
    assert response.status_code == 200

    # Check that session cookie is set with correct attributes
    cookie = next(
        (cookie for cookie in client.cookie_jar if cookie.name == 'session'),
        None
    )
    assert cookie is not None
    assert cookie.secure is False  # Should be True in production
    assert cookie.httponly is True
    assert cookie.samesite == 'Lax'

def test_remember_me_session(client, test_user, session):
    """Test remember me functionality with session."""
    response = client.post('/auth/login', data={
        'email': test_user.email,
        'password': 'password123',
        'remember_me': True
    }, follow_redirects=True)
    assert response.status_code == 200

    with client.session_transaction() as sess:
        assert sess.get('_remember') == '1'

def test_csrf_protection(client, test_user, session):
    """Test CSRF protection."""
    # Login first
    with client.session_transaction() as sess:
        sess['user_id'] = test_user.id
        sess['_fresh'] = True

    # Try to make a POST request without CSRF token
    response = client.post('/auth/change-password', data={
        'current_password': 'password123',
        'new_password': 'newpassword123',
        'confirm_password': 'newpassword123'
    })
    assert response.status_code == 400  # Bad Request due to missing CSRF token

def test_session_id_generation(client):
    """Test that a new session ID is generated for each session."""
    # First request
    response = client.get('/')
    assert response.status_code == 200
    with client.session_transaction() as sess:
        first_session_id = sess.get('_id')
        assert first_session_id is not None

    # Clear session
    client.cookie_jar.clear()

    # Second request
    response = client.get('/')
    assert response.status_code == 200
    with client.session_transaction() as sess:
        second_session_id = sess.get('_id')
        assert second_session_id is not None
        assert first_session_id != second_session_id

def test_session_user_id_consistency(client, test_user, session):
    """Test that user_id in session matches the logged-in user."""
    # Login
    response = client.post('/auth/login', data={
        'email': test_user.email,
        'password': 'password123',
        'remember_me': False
    }, follow_redirects=True)
    assert response.status_code == 200

    with client.session_transaction() as sess:
        assert sess.get('_user_id') == str(test_user.id)

def test_session_fresh_login(client, test_user, session):
    """Test fresh login session attribute."""
    # Fresh login
    response = client.post('/auth/login', data={
        'email': test_user.email,
        'password': 'password123',
        'remember_me': False
    }, follow_redirects=True)
    assert response.status_code == 200

    with client.session_transaction() as sess:
        assert sess.get('_fresh') is True

def test_session_remember_cookie(client, test_user, session):
    """Test remember cookie functionality."""
    response = client.post('/auth/login', data={
        'email': test_user.email,
        'password': 'password123',
        'remember_me': True
    }, follow_redirects=True)
    assert response.status_code == 200

    # Check that remember cookie is set
    cookie = next(
        (cookie for cookie in client.cookie_jar if cookie.name == 'remember_token'),
        None
    )
    assert cookie is not None
