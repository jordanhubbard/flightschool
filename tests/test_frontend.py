import pytest
from flask import session
from flask_login import current_user
from app.models import User, Aircraft, Booking
from app import db
from datetime import datetime, timedelta

def test_home_page(client):
    """Test the home page is accessible and contains expected content"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Next Level Tailwheel' in response.data
    assert b'Your trusted partner in flight training' in response.data
    assert b'Sign In' in response.data

def test_admin_dashboard_ui(client, test_admin, app):
    """Test admin dashboard UI elements."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True

        response = client.get('/admin/dashboard')
        assert response.status_code == 200
        assert b'Admin Dashboard' in response.data
        assert b'User Management' in response.data
        assert b'Aircraft Management' in response.data

def test_aircraft_management_ui(client, test_admin, app):
    """Test aircraft management UI elements."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True

        response = client.get('/admin/aircraft')
        assert response.status_code == 200
        assert b'Aircraft Management' in response.data
        assert b'Add Aircraft' in response.data

def test_instructor_management_ui(client, test_admin, app):
    """Test instructor management UI elements."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True

        response = client.get('/admin/instructors')
        assert response.status_code == 200
        assert b'Instructor Management' in response.data
        assert b'Add Instructor' in response.data

def test_booking_dashboard_ui(client, test_user, app):
    """Test booking dashboard UI elements."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.id
            sess['_fresh'] = True

        response = client.get('/booking/dashboard')
        assert response.status_code == 200
        assert b'My Schedule' in response.data
        assert b'Book a Flight' in response.data

def test_booking_list_ui(client, test_user, app):
    """Test booking list UI elements."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.id
            sess['_fresh'] = True

        response = client.get('/booking/list')
        assert response.status_code == 200
        assert b'My Bookings' in response.data

def test_navigation_ui(client, test_user, app):
    """Test navigation UI elements."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.id
            sess['_fresh'] = True

        response = client.get('/')
        assert response.status_code == 200
        assert b'My Schedule' in response.data
        assert b'Account Settings' in response.data
        assert b'Logout' in response.data

def test_instructor_add_ui(client, test_admin, app):
    """Test instructor add form UI elements."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True

        response = client.get('/admin/user/create')
        assert response.status_code == 200
        assert b'Add New User' in response.data
        assert b'Email' in response.data
        assert b'First Name' in response.data
        assert b'Last Name' in response.data
        assert b'Role' in response.data

def test_instructor_delete_ui(client, test_admin, test_instructor, app):
    """Test instructor delete UI elements."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True

        response = client.get(f'/admin/user/{test_instructor.id}')
        assert response.status_code == 200
        assert b'Delete User' in response.data

def test_instructor_management_navigation(client, test_admin, app):
    """Test instructor management navigation elements."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True

        response = client.get('/admin/instructors')
        assert response.status_code == 200
        assert b'Add Instructor' in response.data
        assert b'View All Instructors' in response.data

def test_user_management_ui(client, test_admin, app):
    """Test user management UI elements."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True

        response = client.get('/admin/users')
        assert response.status_code == 200
        assert b'User Management' in response.data
        assert b'Add User' in response.data

def test_user_status_ui(client, test_admin, test_user, app):
    """Test user status UI elements."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True

        response = client.get(f'/admin/user/{test_user.id}')
        assert response.status_code == 200
        assert b'Status' in response.data
        assert b'Active' in response.data

def test_instructor_dashboard_ui(client, test_instructor, app):
    """Test instructor dashboard UI elements."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_instructor.id
            sess['_fresh'] = True

        response = client.get('/instructor/dashboard')
        assert response.status_code == 200
        assert b'Instructor Dashboard' in response.data
        assert b'My Students' in response.data

def test_user_profile_ui(client, test_user, app):
    """Test user profile UI elements."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.id
            sess['_fresh'] = True

        response = client.get('/auth/account-settings')
        assert response.status_code == 200
        assert b'Account Settings' in response.data
        assert b'Update Profile' in response.data

def test_error_pages(client):
    """Test error pages"""
    # Test 404 page
    response = client.get('/nonexistent-page')
    assert response.status_code == 404
    assert b'Page Not Found' in response.data
    assert b'The page you are looking for does not exist.' in response.data 