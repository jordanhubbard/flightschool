import pytest
from flask_login import current_user
from app.models import User

def test_register(client):
    response = client.post('/auth/register', data={
        'email': 'new@example.com',
        'password': 'password123',
        'first_name': 'New',
        'last_name': 'User',
        'address': '123 Main St',
        'phone': '123-456-7890'
    }, follow_redirects=True)
    assert b'Registration successful' in response.data

def test_register_existing_email(client, test_user):
    response = client.post('/auth/register', data={
        'email': 'test@example.com',
        'password': 'password123',
        'first_name': 'Test',
        'last_name': 'User',
        'address': '123 Main St',
        'phone': '123-456-7890'
    }, follow_redirects=True)
    assert b'Email already registered' in response.data

def test_login(client, test_user):
    response = client.post('/auth/login', data={
        'email': 'test@example.com',
        'password': 'password123'
    }, follow_redirects=True)
    assert b'Book a Flight' in response.data

def test_login_invalid_credentials(client, test_user):
    response = client.post('/auth/login', data={
        'email': 'test@example.com',
        'password': 'wrongpassword'
    }, follow_redirects=True)
    assert b'Invalid email or password' in response.data

def test_logout(client, test_user):
    client.post('/auth/login', data={
        'email': 'test@example.com',
        'password': 'password123'
    })
    response = client.get('/auth/logout', follow_redirects=True)
    assert b'You have been logged out' in response.data
    assert not current_user.is_authenticated 