import pytest
from datetime import datetime, timedelta
from app.models import User, Aircraft, Booking
from app import db

def test_home_page(client):
    """Test the home page is accessible and contains expected content"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Eyes Outside Aviation' in response.data

def test_admin_dashboard_ui(client, test_admin, test_aircraft, test_instructor, test_user):
    """Test the admin dashboard UI elements and functionality"""
    # Login as admin
    client.post('/login', data={
        'email': 'admin@example.com',
        'password': 'admin123'
    })
    
    # Test dashboard access
    response = client.get('/admin/')
    assert response.status_code == 200
    assert b'Admin Dashboard' in response.data
    
    # Test aircraft management section
    assert b'Aircraft Management' in response.data
    assert b'Add New Aircraft' in response.data
    assert b'N12345' in response.data  # test_aircraft tail number
    
    # Test master schedule section
    assert b'Master Schedule' in response.data

def test_aircraft_management_ui(client, test_admin, test_aircraft):
    """Test the aircraft management UI and functionality"""
    client.post('/login', data={
        'email': 'admin@example.com',
        'password': 'admin123'
    })
    
    # Test aircraft list page
    response = client.get('/admin/')
    assert response.status_code == 200
    assert b'Aircraft Management' in response.data
    assert b'N12345' in response.data
    assert b'Add New Aircraft' in response.data
    
    # Test edit aircraft button
    assert b'Edit' in response.data

def test_instructor_management_ui(client, test_admin, test_instructor):
    """Test the instructor management UI and functionality"""
    client.post('/login', data={
        'email': 'admin@example.com',
        'password': 'admin123'
    })
    
    # Test instructor list
    response = client.get('/admin/')
    assert response.status_code == 200
    assert b'John' in response.data  # test_instructor first name
    assert b'Doe' in response.data   # test_instructor last name
    assert b'instructor@example.com' in response.data

def test_booking_dashboard_ui(client, test_user, test_aircraft, test_instructor):
    """Test the booking dashboard UI and functionality"""
    client.post('/login', data={
        'email': 'test@example.com',
        'password': 'password123'
    })
    
    # Test booking dashboard access
    response = client.get('/booking/dashboard')
    assert response.status_code == 200
    assert b'Book a Flight' in response.data
    
    # Test aircraft selection
    assert b'Select Aircraft' in response.data
    assert b'N12345' in response.data  # test_aircraft tail number
    
    # Test instructor selection
    assert b'Select Instructor' in response.data
    assert b'John Doe' in response.data  # test_instructor name
    
    # Test booking form
    assert b'Start Time' in response.data
    assert b'Duration' in response.data
    assert b'Book Flight' in response.data

def test_booking_list_ui(client, test_user, test_aircraft, test_instructor):
    """Test the booking list UI and functionality"""
    client.post('/login', data={
        'email': 'test@example.com',
        'password': 'password123'
    })
    
    # Create a test booking
    start_time = datetime.now() + timedelta(days=1)
    client.post('/booking/book', data={
        'start_time': start_time.strftime('%Y-%m-%dT%H:%M'),
        'duration': '1',
        'aircraft_id': str(test_aircraft.id),
        'instructor_id': str(test_instructor.id)
    }, follow_redirects=True)
    
    # Test booking list display
    response = client.get('/booking/dashboard')
    assert response.status_code == 200
    assert b'Your Upcoming Flights' in response.data
    assert b'N12345' in response.data  # test_aircraft tail number
    assert b'John Doe' in response.data  # test_instructor name
    assert b'Scheduled' in response.data  # booking status

def test_edit_booking_ui(client, test_admin, test_user, test_aircraft, test_instructor):
    """Test the booking edit UI and functionality"""
    # Login as admin
    client.post('/login', data={
        'email': 'admin@example.com',
        'password': 'admin123'
    })
    
    # Create a test booking
    start_time = datetime.now() + timedelta(days=1)
    booking = Booking(
        student_id=test_user.id,
        aircraft_id=test_aircraft.id,
        instructor_id=test_instructor.id,
        start_time=start_time,
        end_time=start_time + timedelta(hours=1),
        status='scheduled'
    )
    db.session.add(booking)
    db.session.commit()
    
    # Test edit booking page
    response = client.get('/admin/')
    assert response.status_code == 200
    assert b'Edit' in response.data
    assert b'Start Time' in response.data
    assert b'End Time' in response.data
    assert b'Status' in response.data

def test_navigation_ui(client, test_user, test_admin):
    """Test the navigation UI and functionality"""
    # Test navigation for non-authenticated user
    response = client.get('/')
    assert response.status_code == 200
    assert b'Home' in response.data
    assert b'Login' in response.data
    
    # Test navigation for regular user
    client.post('/login', data={
        'email': 'test@example.com',
        'password': 'password123'
    })
    response = client.get('/')
    assert response.status_code == 200
    assert b'Book a Flight' in response.data
    assert b'Admin Dashboard' not in response.data
    
    # Test navigation for admin
    client.post('/login', data={
        'email': 'admin@example.com',
        'password': 'admin123'
    })
    response = client.get('/')
    assert response.status_code == 200
    assert b'Admin Dashboard' in response.data
    assert b'Book a Flight' not in response.data 