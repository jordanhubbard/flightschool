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
        'is_instructor': True
    }, follow_redirects=True)
    
    assert b'Instructor added successfully' in response.data
    instructor = User.query.filter_by(email='jane@example.com').first()
    assert instructor is not None
    assert instructor.certificates == 'CFI,CFII'
    assert instructor.is_instructor is True

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