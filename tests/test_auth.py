import pytest
from app.models import User

def test_login(client, test_user, session):
    response = client.post('/auth/login', data={
        'email': test_user.email,
        'password': 'password123',
        'remember_me': False
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Flight Schedule' in response.data
    with client.session_transaction() as sess:
        assert sess.get('_user_id') == str(test_user.id)

def test_login_invalid_credentials(client, test_user, session):
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
    test_user.status = 'inactive'
    session.commit()
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
    response = client.post('/auth/login', data={
        'email': admin_user.email,
        'password': 'password123',
        'remember_me': False
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Admin Dashboard' in response.data
    with client.session_transaction() as sess:
        assert sess.get('_user_id') == str(admin_user.id)

def test_student_login_redirect(client, test_user, session):
    response = client.post('/auth/login', data={
        'email': test_user.email,
        'password': 'password123',
        'remember_me': False
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Flight Schedule' in response.data
    with client.session_transaction() as sess:
        assert sess.get('_user_id') == str(test_user.id)

def test_logout(client, test_user, session):
    client.post('/auth/login', data={
        'email': test_user.email,
        'password': 'password123',
        'remember_me': False
    }, follow_redirects=True)
    response = client.get('/auth/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'Sign In' in response.data
    with client.session_transaction() as sess:
        assert sess.get('_user_id') is None

def test_login_required(client):
    response = client.get('/booking/dashboard', follow_redirects=True)
    assert response.status_code == 200
    assert b'Sign In' in response.data

def test_remember_me(client, test_user, session):
    response = client.post('/auth/login', data={
        'email': test_user.email,
        'password': 'password123',
        'remember_me': True
    }, follow_redirects=True)
    assert response.status_code == 200
    assert 'remember_token' in response.headers.get('Set-Cookie', '')

def test_register(client):
    response = client.post('/auth/register', data={
        'first_name': 'New',
        'last_name': 'User',
        'email': 'newuser@example.com',
        'password': 'newpassword',
        'confirm': 'newpassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Account created' in response.data
    response = client.post('/auth/login', data={
        'email': 'newuser@example.com',
        'password': 'newpassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Flight Schedule' in response.data

def test_change_password(client, test_user, session):
    client.post('/auth/login', data={
        'email': test_user.email,
        'password': 'password123',
    }, follow_redirects=True)
    response = client.post('/auth/account_settings', data={
        'current_password': 'password123',
        'new_password': 'newpass',
        'confirm': 'newpass'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Password updated' in response.data
    client.get('/auth/logout', follow_redirects=True)
    response = client.post('/auth/login', data={
        'email': test_user.email,
        'password': 'newpass'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Flight Schedule' in response.data

def test_update_profile(client, test_user, session):
    client.post('/auth/login', data={
        'email': test_user.email,
        'password': 'password123',
    }, follow_redirects=True)
    response = client.post('/auth/account_settings', data={
        'first_name': 'Updated',
        'last_name': 'Name',
        'phone': '555-9999',
        'certificates': 'PPL, IR'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Profile updated' in response.data
    updated_user = User.query.filter_by(email=test_user.email).first()
    assert updated_user.first_name == 'Updated'
    assert updated_user.last_name == 'Name'
    assert updated_user.phone == '555-9999'
    assert 'IR' in updated_user.certificates
