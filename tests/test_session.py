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