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
    
    # First get the form to get the CSRF token
    response = client.get('/admin/aircraft/create')
    assert response.status_code == 200
    
    # Now submit the form with the CSRF token
    response = client.post('/admin/aircraft/create', data={
        'registration': 'N54321',
        'make_model': 'Piper Cherokee',
        'year': '2019',
        'status': 'active'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Aircraft created successfully' in response.data

def test_edit_aircraft(client, test_admin, test_aircraft, app):
    """Test editing an existing aircraft."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    # First get the form to get the CSRF token
    response = client.get(f'/admin/aircraft/{test_aircraft.id}/edit')
    assert response.status_code == 200
    
    # Now submit the form with the CSRF token
    response = client.post(f'/admin/aircraft/{test_aircraft.id}/edit', data={
        'registration': 'N54321',
        'make_model': 'Piper Cherokee',
        'year': '2019',
        'status': 'active'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Aircraft updated successfully' in response.data

def test_add_instructor(client, test_admin, app):
    """Test adding a new instructor."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    # First get the form to get the CSRF token
    response = client.get('/admin/user/create?type=instructor')
    assert response.status_code == 200
    
    # Now submit the form with the CSRF token
    response = client.post('/admin/user/create', data={
        'email': 'new.instructor@example.com',
        'first_name': 'New',
        'last_name': 'Instructor',
        'phone': '123-456-7890',
        'certificates': 'CFI',
        'status': 'active',
        'role': 'instructor'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'User created successfully' in response.data

def test_add_student(client, test_admin, app):
    """Test adding a new student."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    # First get the form to get the CSRF token
    response = client.get('/admin/user/create?type=student')
    assert response.status_code == 200
    
    # Now submit the form with the CSRF token
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

def test_add_instructor_duplicate_email(client, test_admin, test_instructor, app):
    """Test adding an instructor with a duplicate email."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    # First get the form to get the CSRF token
    response = client.get('/admin/user/create?type=instructor')
    assert response.status_code == 200
    
    # Now submit the form with the CSRF token
    response = client.post('/admin/user/create', data={
        'email': test_instructor.email,  # Using existing instructor's email
        'first_name': 'John',
        'last_name': 'Doe',
        'phone': '123-456-7890',
        'certificates': 'CFI',
        'status': 'active',
        'role': 'instructor'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Email already registered' in response.data

def test_edit_instructor(client, test_admin, test_instructor, app):
    """Test editing an existing instructor."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    # First get the form to get the CSRF token
    response = client.get(f'/admin/user/{test_instructor.id}/edit')
    assert response.status_code == 200
    
    # Now submit the form with the CSRF token
    response = client.post(f'/admin/user/{test_instructor.id}/edit', data={
        'email': 'john.updated@example.com',
        'first_name': 'Johnny',
        'last_name': 'Smith',
        'phone': '555-555-5555',
        'certificates': 'CFI, CFII, MEI',
        'status': 'active',
        'role': 'instructor'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'User updated successfully' in response.data

def test_edit_instructor_invalid_data(client, test_admin, test_instructor, app):
    """Test editing an instructor with invalid data."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    # First get the form to get the CSRF token
    response = client.get(f'/admin/user/{test_instructor.id}/edit')
    assert response.status_code == 200
    
    # Now submit the form with the CSRF token
    response = client.post(f'/admin/user/{test_instructor.id}/edit', data={
        'first_name': 'Johnny',
        'last_name': 'Smith',
        'email': 'invalid-email',  # Invalid email format
        'phone': '555-555-5555',
        'certificates': 'CFI, CFII, MEI',
        'status': 'active',
        'role': 'instructor'
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

def test_instructor_status_management(client, test_admin, test_instructor, app):
    """Test managing instructor status."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.put(f'/admin/user/{test_instructor.id}/status',
        json={'status': 'inactive'},
        headers={'Content-Type': 'application/json'}
    )
    assert response.status_code == 200

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