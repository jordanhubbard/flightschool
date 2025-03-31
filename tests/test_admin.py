import pytest
from app.models import Aircraft, User, Booking
from datetime import datetime
from flask import session
from app import db

def test_admin_dashboard_access(client, test_admin, app):
    """Test admin dashboard access."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.get('/admin/dashboard')
    assert response.status_code == 200
    assert b'Admin Dashboard' in response.data

def test_admin_dashboard_unauthorized(client, test_user, app):
    """Test unauthorized access to admin dashboard."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.id
            sess['_fresh'] = True
    
    response = client.get('/admin/dashboard')
    assert response.status_code == 403
    assert b'Admin access required' in response.data

def test_add_aircraft(client, test_admin, app):
    """Test adding a new aircraft."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.post('/admin/aircraft/add', data={
        'registration': 'N54321',
        'make_model': 'Cessna 172',
        'year': '2020',
        'status': 'available',
        'rate_per_hour': '150.00'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Aircraft added successfully' in response.data

    aircraft = Aircraft.query.filter_by(registration='N54321').first()
    assert aircraft is not None
    assert aircraft.make_model == 'Cessna 172'
    assert aircraft.year == 2020
    assert aircraft.status == 'available'
    assert aircraft.rate_per_hour == 150.00

def test_edit_aircraft(client, test_admin, test_aircraft, app):
    """Test editing an existing aircraft."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.post(f'/admin/aircraft/{test_aircraft.id}/edit', data={
        'registration': 'N54321',
        'make_model': 'Piper Cherokee',
        'year': '2019',
        'status': 'active',
        'rate_per_hour': '175.00'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Aircraft updated successfully' in response.data

    # Verify the changes in the database
    aircraft = Aircraft.query.get(test_aircraft.id)
    assert aircraft.registration == 'N54321'
    assert aircraft.make_model == 'Piper Cherokee'
    assert aircraft.year == 2019
    assert aircraft.status == 'active'
    assert aircraft.rate_per_hour == 175.00

def test_add_instructor(client, test_admin, app):
    """Test adding a new instructor."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.post('/admin/user/create', data={
        'email': 'new.instructor@example.com',
        'first_name': 'New',
        'last_name': 'Instructor',
        'phone': '123-456-7890',
        'certificates': 'CFI',
        'status': 'active',
        'role': 'instructor',
        'instructor_rate_per_hour': '75.00'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'User created successfully' in response.data

    # Verify the instructor was created
    instructor = User.query.filter_by(email='new.instructor@example.com').first()
    assert instructor is not None
    assert instructor.role == 'instructor'
    assert instructor.instructor_rate_per_hour == 75.00

def test_add_student(client, test_admin, app):
    """Test adding a new student."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.post('/admin/user/create', data={
        'email': 'new.student@example.com',
        'first_name': 'New',
        'last_name': 'Student',
        'phone': '123-456-7890',
        'student_id': 'STU001',
        'status': 'active',
        'role': 'student'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'User created successfully' in response.data

    # Verify the student was created
    student = User.query.filter_by(email='new.student@example.com').first()
    assert student is not None
    assert student.role == 'student'
    assert student.student_id == 'STU001'

def test_add_instructor_duplicate_email(client, test_admin, test_instructor, app):
    """Test adding an instructor with a duplicate email."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.post('/admin/user/create', data={
        'email': test_instructor.email,  # Using existing instructor's email
        'first_name': 'John',
        'last_name': 'Doe',
        'phone': '123-456-7890',
        'certificates': 'CFI',
        'status': 'active',
        'role': 'instructor',
        'instructor_rate_per_hour': '75.00'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Email already registered' in response.data

def test_edit_instructor(client, test_admin, test_instructor, app):
    """Test editing an existing instructor."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.post(f'/admin/user/{test_instructor.id}/edit', data={
        'email': 'john.updated@example.com',
        'first_name': 'Johnny',
        'last_name': 'Smith',
        'phone': '555-555-5555',
        'certificates': 'CFI, CFII, MEI',
        'status': 'active',
        'role': 'instructor',
        'instructor_rate_per_hour': '85.00'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'User updated successfully' in response.data

    # Verify the changes in the database
    instructor = User.query.get(test_instructor.id)
    assert instructor.email == 'john.updated@example.com'
    assert instructor.first_name == 'Johnny'
    assert instructor.certificates == 'CFI, CFII, MEI'
    assert instructor.instructor_rate_per_hour == 85.00

def test_edit_instructor_invalid_data(client, test_admin, test_instructor, app):
    """Test editing an instructor with invalid data."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.post(f'/admin/user/{test_instructor.id}/edit', data={
        'first_name': 'Johnny',
        'last_name': 'Smith',
        'email': 'invalid-email',  # Invalid email format
        'phone': '555-555-5555',
        'certificates': 'CFI, CFII, MEI',
        'status': 'active',
        'role': 'instructor',
        'instructor_rate_per_hour': '85.00'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Invalid email address' in response.data

def test_edit_instructor_nonexistent(client, test_admin, app):
    """Test editing a nonexistent instructor."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.get('/admin/user/99999/edit')
    assert response.status_code == 404

def test_instructor_status_invalid(client, test_admin, test_instructor, app):
    """Test setting an invalid instructor status."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.put(f'/admin/user/{test_instructor.id}/status',
        json={'status': 'invalid_status'},
        headers={'Content-Type': 'application/json'}
    )
    assert response.status_code == 400
    assert b'Invalid status' in response.data

def test_delete_aircraft(client, test_admin, test_aircraft, app):
    """Test deleting an aircraft."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.delete(f'/admin/aircraft/{test_aircraft.id}')
    assert response.status_code == 204

    # Verify the aircraft was deleted
    aircraft = Aircraft.query.get(test_aircraft.id)
    assert aircraft is None

def test_instructor_status_management(client, test_admin, test_instructor, app):
    """Test managing instructor status."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
            
    # Test setting instructor to inactive
    response = client.put(f'/admin/user/{test_instructor.id}/status',
        json={'status': 'inactive'},
        headers={'Content-Type': 'application/json'}
    )
    assert response.status_code == 200
    
    # Verify the status change
    instructor = User.query.get(test_instructor.id)
    assert instructor.status == 'inactive'
    
    # Test setting instructor back to active
    response = client.put(f'/admin/user/{test_instructor.id}/status',
        json={'status': 'active'},
        headers={'Content-Type': 'application/json'}
    )
    assert response.status_code == 200
    
    # Verify the status change
    instructor = User.query.get(test_instructor.id)
    assert instructor.status == 'active'

def test_aircraft_status_management(client, test_admin, test_aircraft, app):
    """Test managing aircraft status."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.put(f'/admin/aircraft/{test_aircraft.id}/status',
        json={'status': 'maintenance'},
        headers={'Content-Type': 'application/json'}
    )
    assert response.status_code == 200

def test_delete_instructor(client, test_admin, test_instructor, app):
    """Test deleting an instructor."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.delete(f'/admin/user/{test_instructor.id}')
    assert response.status_code == 204

def test_delete_instructor_unauthorized(client, test_user, app):
    """Test unauthorized instructor deletion."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.id
            sess['_fresh'] = True
    
    response = client.delete('/admin/user/1')
    assert response.status_code == 403

def test_delete_instructor_nonexistent(client, test_admin, app):
    """Test deleting a nonexistent instructor."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.delete('/admin/user/99999')
    assert response.status_code == 404

def test_edit_student(client, test_admin, test_user, app):
    """Test editing a student."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    # First get the form to get the CSRF token
    response = client.get(f'/admin/user/{test_user.id}/edit')
    assert response.status_code == 200
    
    # Now submit the form with the CSRF token
    response = client.post(f'/admin/user/{test_user.id}/edit', data={
        'email': 'student.updated@example.com',
        'first_name': 'Updated',
        'last_name': 'Student',
        'phone': '555-555-5555',
        'student_id': 'STU002',
        'status': 'inactive',
        'role': 'student'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'User updated successfully' in response.data

def test_delete_student(client, test_admin, test_user, app):
    """Test deleting a student."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.delete(f'/admin/user/{test_user.id}')
    assert response.status_code == 204

def test_user_status_management(client, test_admin, test_user, app):
    """Test managing user status."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.put(f'/admin/user/{test_user.id}/status',
        json={'status': 'inactive'},
        headers={'Content-Type': 'application/json'}
    )
    assert response.status_code == 200

def test_user_status_invalid(client, test_admin, test_user, app):
    """Test setting an invalid user status."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.put(f'/admin/user/{test_user.id}/status',
        json={'status': 'invalid_status'},
        headers={'Content-Type': 'application/json'}
    )
    assert response.status_code == 400
    assert b'Invalid status' in response.data 