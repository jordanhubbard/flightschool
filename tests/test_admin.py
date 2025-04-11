import pytest
from app.models import Aircraft, User, Booking
from datetime import datetime
from flask import session
from app import db

def test_admin_dashboard_access(client, test_admin, session):
    """Test admin dashboard access."""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_admin.id
        sess['_fresh'] = True
    
    response = client.get('/admin/dashboard')
    assert response.status_code == 200
    assert b'Admin Dashboard' in response.data

def test_admin_dashboard_unauthorized(client, test_user, session):
    """Test unauthorized access to admin dashboard."""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_user.id
        sess['_fresh'] = True
    
    response = client.get('/admin/dashboard', follow_redirects=True)
    assert response.status_code == 200
    assert b'Admin access required' in response.data

def test_add_aircraft(client, test_admin, app):
    """Test adding a new aircraft."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_admin.id
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
            sess['_user_id'] = test_admin.id
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

def test_add_instructor(client, test_admin, session):
    """Test adding a new instructor."""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_admin.id
        sess['_fresh'] = True
    
    response = client.post('/admin/instructors/add', data={
        'email': 'new_instructor@example.com',
        'password': 'password123',
        'first_name': 'New',
        'last_name': 'Instructor',
        'role': 'instructor',
        'is_active': True
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Instructor added successfully' in response.data

def test_add_student(client, test_admin, session):
    """Test adding a new student."""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_admin.id
        sess['_fresh'] = True
    
    response = client.post('/admin/students/add', data={
        'email': 'new_student@example.com',
        'password': 'password123',
        'first_name': 'New',
        'last_name': 'Student',
        'role': 'student',
        'is_active': True
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Student added successfully' in response.data

def test_add_instructor_duplicate_email(client, test_admin, test_instructor, app):
    """Test adding an instructor with a duplicate email."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_admin.id
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

def test_edit_instructor(client, test_admin, test_instructor, session):
    """Test editing an instructor."""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_admin.id
        sess['_fresh'] = True
    
    response = client.post(f'/admin/instructors/{test_instructor.id}/edit', data={
        'email': 'updated_instructor@example.com',
        'first_name': 'Updated',
        'last_name': 'Instructor',
        'is_active': True
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Instructor updated successfully' in response.data

def test_edit_instructor_invalid_data(client, test_admin, test_instructor, session):
    """Test editing an instructor with invalid data."""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_admin.id
        sess['_fresh'] = True
    
    response = client.post(f'/admin/instructors/{test_instructor.id}/edit', data={
        'email': 'invalid_email',
        'first_name': 'Updated',
        'last_name': 'Instructor',
        'is_active': True
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Invalid email address' in response.data

def test_edit_instructor_nonexistent(client, test_admin, session):
    """Test editing a nonexistent instructor."""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_admin.id
        sess['_fresh'] = True
    
    response = client.post('/admin/instructors/999/edit', data={
        'email': 'updated_instructor@example.com',
        'first_name': 'Updated',
        'last_name': 'Instructor',
        'is_active': True
    }, follow_redirects=True)
    assert response.status_code == 404

def test_instructor_status_invalid(client, test_admin, test_instructor, app):
    """Test setting an invalid instructor status."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_admin.id
            sess['_fresh'] = True

        response = client.put(f'/admin/user/{test_instructor.id}/status',
            json={'status': 'invalid_status'},
            headers={'Content-Type': 'application/json'}
        )
        assert response.status_code == 400

def test_delete_aircraft(client, test_admin, test_aircraft, app):
    """Test deleting an aircraft."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_admin.id
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
            sess['_user_id'] = test_admin.id
            sess['_fresh'] = True

        # Test setting instructor to inactive
        response = client.put(f'/admin/user/{test_instructor.id}/status',
            json={'status': 'inactive'},
            headers={'Content-Type': 'application/json'}
        )
        assert response.status_code == 200
        assert b'Status updated successfully' in response.data

def test_aircraft_status_management(client, test_admin, test_aircraft, app):
    """Test managing aircraft status."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.put(f'/admin/aircraft/{test_aircraft.id}/status',
        json={'status': 'maintenance'},
        headers={'Content-Type': 'application/json'}
    )
    assert response.status_code == 200

def test_delete_instructor(client, test_admin, test_instructor, session):
    """Test deleting an instructor."""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_admin.id
        sess['_fresh'] = True
    
    response = client.post(f'/admin/instructors/{test_instructor.id}/delete', follow_redirects=True)
    assert response.status_code == 200
    assert b'Instructor deleted successfully' in response.data

def test_delete_instructor_unauthorized(client, test_user, test_instructor, session):
    """Test unauthorized deletion of an instructor."""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_user.id
        sess['_fresh'] = True
    
    response = client.post(f'/admin/instructors/{test_instructor.id}/delete', follow_redirects=True)
    assert response.status_code == 200
    assert b'Admin access required' in response.data

def test_delete_instructor_nonexistent(client, test_admin, session):
    """Test deleting a nonexistent instructor."""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_admin.id
        sess['_fresh'] = True
    
    response = client.post('/admin/instructors/999/delete', follow_redirects=True)
    assert response.status_code == 404

def test_edit_student(client, test_admin, test_user, session):
    """Test editing a student."""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_admin.id
        sess['_fresh'] = True
    
    response = client.post(f'/admin/students/{test_user.id}/edit', data={
        'email': 'updated_student@example.com',
        'first_name': 'Updated',
        'last_name': 'Student',
        'is_active': True
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Student updated successfully' in response.data

def test_delete_student(client, test_admin, test_user, session):
    """Test deleting a student."""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_admin.id
        sess['_fresh'] = True
    
    response = client.post(f'/admin/students/{test_user.id}/delete', follow_redirects=True)
    assert response.status_code == 200
    assert b'Student deleted successfully' in response.data

def test_user_status_management(client, test_admin, test_user, session):
    """Test managing user status."""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_admin.id
        sess['_fresh'] = True
    
    # Deactivate user
    response = client.post(f'/admin/users/{test_user.id}/status', data={
        'status': 'inactive'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'User status updated successfully' in response.data
    
    # Reactivate user
    response = client.post(f'/admin/users/{test_user.id}/status', data={
        'status': 'active'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'User status updated successfully' in response.data

def test_user_status_invalid(client, test_admin, test_user, session):
    """Test invalid user status update."""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_admin.id
        sess['_fresh'] = True
    
    response = client.post(f'/admin/users/{test_user.id}/status', data={
        'status': 'invalid_status'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Invalid status' in response.data 