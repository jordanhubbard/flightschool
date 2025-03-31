import pytest
from datetime import datetime, timedelta
from app.models import User, Aircraft, Booking
from app import db

def test_home_page(client):
    """Test the home page is accessible and contains expected content"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Next Level Tailwheel' in response.data

def test_admin_dashboard_ui(client, test_admin, test_aircraft, test_instructor, test_user):
    """Test the admin dashboard UI elements and functionality"""
    # Login as admin
    client.post('/auth/login', data={
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
    client.post('/auth/login', data={
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
    client.post('/auth/login', data={
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
    client.post('/auth/login', data={
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
    client.post('/auth/login', data={
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
    client.post('/auth/login', data={
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
    client.post('/auth/login', data={
        'email': 'test@example.com',
        'password': 'password123'
    })
    response = client.get('/')
    assert response.status_code == 200
    assert b'Book a Flight' in response.data
    assert b'Admin Dashboard' not in response.data
    
    # Test navigation for admin
    client.post('/auth/login', data={
        'email': 'admin@example.com',
        'password': 'admin123'
    })
    response = client.get('/')
    assert response.status_code == 200
    assert b'Admin Dashboard' in response.data
    assert b'Book a Flight' not in response.data

def test_instructor_add_ui(client, test_admin):
    client.post('/auth/login', data={
        'email': 'admin@example.com',
        'password': 'admin123'
    })
    
    # Test accessing the instructor add page
    response = client.get('/admin/instructor/add', follow_redirects=True)
    assert b'Add New Instructor' in response.data
    assert b'Email' in response.data
    assert b'Password' in response.data
    assert b'First Name' in response.data
    assert b'Last Name' in response.data
    assert b'Phone' in response.data
    assert b'Certificates and Ratings' in response.data
    
    # Verify certificate checkboxes are present
    assert b'Certified Flight Instructor (CFI)' in response.data
    assert b'Certified Flight Instructor - Instrument (CFII)' in response.data
    assert b'Multi-Engine Instructor (MEI)' in response.data
    
    # Test form submission with multiple certificates
    response = client.post('/admin/instructor/add', data={
        'email': 'jane@example.com',
        'password': 'instructor123',
        'first_name': 'Jane',
        'last_name': 'Smith',
        'phone': '987-654-3210',
        'certificates': ['CFI', 'CFII'],  # Multiple certificates as a list
        'csrf_token': 'test_token'
    }, follow_redirects=True)
    
    assert b'Instructor added successfully' in response.data
    assert b'jane@example.com' in response.data
    assert b'Jane Smith' in response.data
    assert b'CFI, CFII' in response.data

def test_instructor_edit_ui(client, test_admin, test_instructor):
    client.post('/auth/login', data={
        'email': 'admin@example.com',
        'password': 'admin123'
    })
    
    # Test accessing the instructor edit page
    response = client.get(f'/admin/instructor/{test_instructor.id}/edit', follow_redirects=True)
    assert b'Edit Instructor' in response.data
    assert b'instructor@example.com' in response.data
    assert b'John' in response.data
    assert b'Doe' in response.data
    assert b'123-456-7890' in response.data
    assert b'CFI, CFII' in response.data  # Updated to match new format with space after comma
    
    # Test editing the instructor
    response = client.post(f'/admin/instructor/{test_instructor.id}/edit', data={
        'first_name': 'Johnny',
        'last_name': 'Smith',
        'email': 'johnny@example.com',
        'phone': '555-555-5555',
        'certificates': ['CFI', 'CFII', 'MEI'],  # Multiple certificates as a list
        'status': 'unavailable',
        'csrf_token': 'test_token'
    }, follow_redirects=True)
    
    assert b'Instructor updated successfully' in response.data
    assert b'Johnny' in response.data
    assert b'CFI, CFII, MEI' in response.data  # Updated to match new format with spaces after commas

def test_instructor_delete_ui(client, test_admin, test_instructor):
    client.post('/auth/login', data={
        'email': 'admin@example.com',
        'password': 'admin123'
    })
    
    # Test accessing the instructor list page
    response = client.get('/admin/instructor/', follow_redirects=True)
    assert b'instructor@example.com' in response.data
    assert b'John Doe' in response.data
    
    # Test delete confirmation dialog
    response = client.get(f'/admin/user/{test_instructor.id}/delete', follow_redirects=True)
    assert b'Are you sure you want to delete this instructor?' in response.data
    
    # Test actual deletion
    response = client.post(f'/admin/user/{test_instructor.id}/delete', follow_redirects=True)
    assert b'User deleted successfully' in response.data
    assert b'instructor@example.com' not in response.data
    assert b'John Doe' not in response.data

def test_instructor_status_ui(client, test_admin, test_instructor):
    client.post('/auth/login', data={
        'email': 'admin@example.com',
        'password': 'admin123'
    })
    
    # Test accessing the instructor list page
    response = client.get('/admin/instructor/', follow_redirects=True)
    assert b'instructor@example.com' in response.data
    assert b'Active' in response.data
    
    # Test status update form
    response = client.get(f'/admin/instructor/{test_instructor.id}/status', follow_redirects=True)
    assert b'Update Instructor Status' in response.data
    assert b'Status' in response.data
    
    # Test setting status to unavailable
    response = client.post(f'/admin/instructor/{test_instructor.id}/status', data={
        'status': 'unavailable',
        'csrf_token': 'test_token'
    }, follow_redirects=True)
    assert b'Instructor status updated successfully' in response.data
    assert b'Unavailable' in response.data
    
    # Test setting status back to active
    response = client.post(f'/admin/instructor/{test_instructor.id}/status', data={
        'status': 'active',
        'csrf_token': 'test_token'
    }, follow_redirects=True)
    assert b'Instructor status updated successfully' in response.data
    assert b'Active' in response.data

def test_instructor_management_navigation(client, test_admin):
    client.post('/auth/login', data={
        'email': 'admin@example.com',
        'password': 'admin123'
    })
    
    # Test navigation to instructor management
    response = client.get('/admin/', follow_redirects=True)
    assert b'Instructor Management' in response.data
    
    # Test instructor list page
    response = client.get('/admin/instructor/', follow_redirects=True)
    assert b'Instructor List' in response.data
    assert b'Add New Instructor' in response.data
    
    # Test instructor add page
    response = client.get('/admin/instructor/add', follow_redirects=True)
    assert b'Add New Instructor' in response.data
    assert b'Back to Instructor List' in response.data 