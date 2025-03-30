import pytest
from app.models import Aircraft, User, Booking

def test_admin_dashboard_access(client, test_admin):
    client.post('/auth/login', data={
        'email': 'admin@example.com',
        'password': 'admin123'
    })
    response = client.get('/admin/', follow_redirects=True)
    assert b'Admin Dashboard' in response.data

def test_admin_dashboard_unauthorized(client, test_user):
    client.post('/auth/login', data={
        'email': 'test@example.com',
        'password': 'password123'
    })
    response = client.get('/admin/', follow_redirects=True)
    assert b'You need to be an admin to access this page' in response.data

def test_add_aircraft(client, test_admin):
    client.post('/auth/login', data={
        'email': 'admin@example.com',
        'password': 'admin123'
    })
    
    response = client.post('/admin/aircraft/add', data={
        'tail_number': 'N67890',
        'make_model': 'Piper Arrow',
        'year': '2021',
        'status': 'available'
    }, follow_redirects=True)
    
    assert b'Aircraft added successfully' in response.data
    aircraft = Aircraft.query.filter_by(tail_number='N67890').first()
    assert aircraft is not None
    assert aircraft.status == 'available'

def test_edit_aircraft(client, test_admin, test_aircraft):
    client.post('/auth/login', data={
        'email': 'admin@example.com',
        'password': 'admin123'
    })
    
    response = client.post(f'/admin/aircraft/{test_aircraft.id}/edit', data={
        'tail_number': 'N54321',
        'make_model': 'Updated Model',
        'year': '2022',
        'status': 'maintenance'
    }, follow_redirects=True)
    
    assert b'Aircraft updated successfully' in response.data
    aircraft = Aircraft.query.get(test_aircraft.id)
    assert aircraft.tail_number == 'N54321'
    assert aircraft.status == 'maintenance'

def test_add_instructor(client, test_admin):
    client.post('/auth/login', data={
        'email': 'admin@example.com',
        'password': 'admin123'
    })
    
    response = client.post('/admin/instructor/add', data={
        'email': 'jane@example.com',
        'password': 'instructor123',
        'first_name': 'Jane',
        'last_name': 'Smith',
        'phone': '987-654-3210',
        'certificates': 'CFI,CFII',
        'is_instructor': True,
        'csrf_token': 'test_token'  # We'll need to get the actual CSRF token in a real test
    }, follow_redirects=True)
    
    assert b'Instructor added successfully' in response.data
    instructor = User.query.filter_by(email='jane@example.com').first()
    assert instructor is not None
    assert instructor.certificates == 'CFI,CFII'
    assert instructor.is_instructor is True
    assert instructor.status == 'available'

def test_add_instructor_duplicate_email(client, test_admin, test_instructor):
    client.post('/auth/login', data={
        'email': 'admin@example.com',
        'password': 'admin123'
    })
    
    response = client.post('/admin/instructor/add', data={
        'email': 'instructor@example.com',  # Using existing instructor's email
        'password': 'newpassword123',
        'first_name': 'John',
        'last_name': 'Doe',
        'phone': '123-456-7890',
        'certificates': 'CFI',
        'is_instructor': True,
        'csrf_token': 'test_token'
    }, follow_redirects=True)
    
    assert b'Email already registered' in response.data
    # Verify no new instructor was created
    instructors = User.query.filter_by(email='instructor@example.com').all()
    assert len(instructors) == 1

def test_edit_instructor(client, test_admin, test_instructor):
    client.post('/auth/login', data={
        'email': 'admin@example.com',
        'password': 'admin123'
    })
    
    response = client.post(f'/admin/instructor/{test_instructor.id}/edit', data={
        'first_name': 'Johnny',
        'last_name': 'Smith',
        'email': 'johnny@example.com',
        'phone': '555-555-5555',
        'certificates': 'CFI,CFII,MEI',
        'status': 'unavailable'
    }, follow_redirects=True)
    
    assert b'Instructor updated successfully' in response.data
    instructor = User.query.get(test_instructor.id)
    assert instructor.first_name == 'Johnny'
    assert instructor.certificates == 'CFI,CFII,MEI'
    assert instructor.status == 'unavailable'

def test_delete_aircraft(client, test_admin, test_aircraft):
    client.post('/auth/login', data={
        'email': 'admin@example.com',
        'password': 'admin123'
    })
    
    response = client.post(f'/admin/aircraft/{test_aircraft.id}/delete', follow_redirects=True)
    assert b'Aircraft deleted successfully' in response.data
    aircraft = Aircraft.query.get(test_aircraft.id)
    assert aircraft is None

def test_instructor_status_management(client, test_admin, test_instructor):
    client.post('/auth/login', data={
        'email': 'admin@example.com',
        'password': 'admin123'
    })
    
    # Test setting instructor as unavailable
    response = client.post(f'/admin/instructor/{test_instructor.id}/status', data={
        'status': 'unavailable'
    }, follow_redirects=True)
    assert b'Instructor status updated successfully' in response.data
    instructor = User.query.get(test_instructor.id)
    assert instructor.status == 'unavailable'
    
    # Test setting instructor as active
    response = client.post(f'/admin/instructor/{test_instructor.id}/status', data={
        'status': 'active'
    }, follow_redirects=True)
    assert b'Instructor status updated successfully' in response.data
    instructor = User.query.get(test_instructor.id)
    assert instructor.status == 'active'

def test_aircraft_status_management(client, test_admin, test_aircraft):
    client.post('/auth/login', data={
        'email': 'admin@example.com',
        'password': 'admin123'
    })
    
    # Test setting aircraft as maintenance
    response = client.post(f'/admin/aircraft/{test_aircraft.id}/status', data={
        'status': 'maintenance'
    }, follow_redirects=True)
    assert b'Aircraft status updated successfully' in response.data
    aircraft = Aircraft.query.get(test_aircraft.id)
    assert aircraft.status == 'maintenance'
    
    # Test setting aircraft as available
    response = client.post(f'/admin/aircraft/{test_aircraft.id}/status', data={
        'status': 'available'
    }, follow_redirects=True)
    assert b'Aircraft status updated successfully' in response.data
    aircraft = Aircraft.query.get(test_aircraft.id)
    assert aircraft.status == 'available'

def test_delete_instructor(client, test_admin, test_instructor):
    client.post('/auth/login', data={
        'email': 'admin@example.com',
        'password': 'admin123'
    })
    
    # First verify the instructor exists
    instructor = User.query.get(test_instructor.id)
    assert instructor is not None
    assert instructor.is_instructor is True
    
    # Try to delete the instructor
    response = client.post(f'/admin/user/{test_instructor.id}/delete', follow_redirects=True)
    assert b'User deleted successfully' in response.data
    
    # Verify the instructor was deleted
    instructor = User.query.get(test_instructor.id)
    assert instructor is None

def test_delete_instructor_unauthorized(client, test_user):
    client.post('/auth/login', data={
        'email': 'test@example.com',
        'password': 'password123'
    })
    
    # Try to delete a user without admin privileges
    response = client.post('/admin/user/1/delete', follow_redirects=True)
    assert b'You need to be an admin to access this page' in response.data 