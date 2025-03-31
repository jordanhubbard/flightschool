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
    assert b'Welcome to Eyes Outside Aviation' in response.data
    assert b'Your trusted partner in flight training' in response.data
    assert b'Login' in response.data

def test_admin_dashboard_ui(client, logged_in_admin):
    """Test the admin dashboard UI elements and functionality"""
    response = client.get('/admin/dashboard')
    assert response.status_code == 200
    assert b'Admin Dashboard' in response.data
    assert b'Instructor Management' in response.data
    assert b'Aircraft Management' in response.data
    assert b'Student Management' in response.data

def test_aircraft_management_ui(client, logged_in_admin, test_aircraft):
    """Test the aircraft management UI and functionality"""
    response = client.get('/admin/aircraft')
    assert response.status_code == 200
    assert b'Aircraft Management' in response.data
    assert b'Add New Aircraft' in response.data
    assert test_aircraft.tail_number.encode() in response.data

def test_instructor_management_ui(client, logged_in_admin, test_instructor):
    """Test the instructor management UI and functionality"""
    response = client.get('/admin/instructors')
    assert response.status_code == 200
    assert b'Instructor Management' in response.data
    assert b'Add New Instructor' in response.data
    assert test_instructor.email.encode() in response.data

def test_booking_dashboard_ui(client, logged_in_user):
    """Test the booking dashboard UI and functionality"""
    response = client.get('/booking/dashboard')
    assert response.status_code == 200
    assert b'My Schedule' in response.data
    assert b'Book a Flight' in response.data

def test_booking_list_ui(client, logged_in_user, test_aircraft):
    """Test the booking list UI and functionality"""
    # Create a test booking
    booking = Booking(
        student_id=logged_in_user.id,
        aircraft_id=test_aircraft.id,
        start_time=datetime.now() + timedelta(days=1),
        end_time=datetime.now() + timedelta(days=1, hours=1),
        status='confirmed'
    )
    db.session.add(booking)
    db.session.commit()
    db.session.refresh(booking)

    response = client.get('/booking/list')
    assert response.status_code == 200
    assert b'My Bookings' in response.data
    assert test_aircraft.tail_number.encode() in response.data

def test_navigation_ui(client, logged_in_user, logged_in_admin):
    """Test the navigation UI and functionality"""
    # Test navigation for non-authenticated user
    client.get('/auth/logout')  # Ensure logged out
    response = client.get('/')
    assert response.status_code == 200
    assert b'Login' in response.data
    assert b'Admin Dashboard' not in response.data
    
    # Test navigation for regular user
    with client.session_transaction() as sess:
        sess['user_id'] = logged_in_user.id
        sess['_fresh'] = True

    response = client.get('/')
    assert response.status_code == 200
    assert b'My Schedule' in response.data
    assert b'Book a Flight' in response.data
    assert b'Admin Dashboard' not in response.data
    
    # Test navigation for admin user
    with client.session_transaction() as sess:
        sess['user_id'] = logged_in_admin.id
        sess['_fresh'] = True

    response = client.get('/')
    assert response.status_code == 200
    assert b'Admin Dashboard' in response.data
    assert b'Instructor Management' in response.data
    assert b'Student Management' in response.data

def test_instructor_add_ui(client, logged_in_admin):
    """Test the instructor creation UI"""
    response = client.get('/admin/user/create?type=instructor')
    assert response.status_code == 200
    assert b'Create New Instructor' in response.data
    assert b'Email' in response.data
    assert b'Password' in response.data
    assert b'First Name' in response.data
    assert b'Last Name' in response.data
    assert b'Phone' in response.data
    assert b'Certificates' in response.data

def test_instructor_delete_ui(client, logged_in_admin, test_instructor):
    """Test the instructor deletion UI"""
    response = client.get('/admin/dashboard')
    assert response.status_code == 200
    assert test_instructor.email.encode() in response.data
    assert b'Delete' in response.data

def test_instructor_management_navigation(client, logged_in_admin):
    """Test navigation to instructor management pages"""
    response = client.get('/admin/dashboard')
    assert response.status_code == 200
    assert b'Instructor Management' in response.data
    
    response = client.get('/admin/instructors')
    assert response.status_code == 200
    assert b'Add New Instructor' in response.data

def test_user_management_ui(client, logged_in_admin):
    """Test the user management UI"""
    response = client.get('/admin/dashboard')
    assert response.status_code == 200
    assert b'Student Management' in response.data
    assert b'Add New Student' in response.data
    
    response = client.get('/admin/user/create?type=student')
    assert response.status_code == 200
    assert b'Create New User' in response.data
    assert b'Email' in response.data
    assert b'Password' in response.data
    assert b'First Name' in response.data
    assert b'Last Name' in response.data
    assert b'Phone' in response.data
    assert b'Student ID' in response.data
    assert b'Status' in response.data

def test_error_pages(client):
    """Test error pages"""
    # Test 404 page
    response = client.get('/nonexistent-page')
    assert response.status_code == 404
    assert b'Page Not Found' in response.data
    assert b'The page you are looking for does not exist.' in response.data

def test_user_status_ui(client, logged_in_user):
    """Test user status UI elements"""
    # Test active user
    response = client.get('/profile')
    assert response.status_code == 200
    assert b'Active' in response.data
    
    # Test inactive user
    logged_in_user.status = 'inactive'
    db.session.commit()
    db.session.refresh(logged_in_user)
    
    response = client.get('/profile')
    assert response.status_code == 200
    assert b'Inactive' in response.data

def test_instructor_dashboard_ui(client, logged_in_instructor):
    """Test instructor dashboard UI elements"""
    response = client.get('/instructor/dashboard')
    assert response.status_code == 200
    assert b'Instructor Dashboard' in response.data
    assert b'My Students' in response.data
    assert b'Schedule' in response.data

def test_user_profile_ui(client, logged_in_user):
    """Test user profile UI elements"""
    response = client.get('/profile')
    assert response.status_code == 200
    assert logged_in_user.email.encode() in response.data
    assert b'Profile Information' in response.data 