import pytest
from app.models import Aircraft, User, Booking
from datetime import datetime
from flask import session
from app import db

def test_admin_dashboard_access(client, logged_in_admin):
    """Test admin dashboard access."""
    response = client.get('/admin/dashboard')
    assert response.status_code == 200
    assert b'Admin Dashboard' in response.data

def test_admin_dashboard_no_access(client, logged_in_student):
    """Test admin dashboard access denied for non-admin."""
    response = client.get('/admin/dashboard')
    assert response.status_code == 403
    assert b'Admin access required' in response.data

def test_admin_dashboard_not_logged_in(client):
    """Test admin dashboard access denied when not logged in."""
    response = client.get('/admin/dashboard')
    assert response.status_code == 302
    assert '/login' in response.location

def test_add_aircraft(client, test_admin, app):
    """Test adding a new aircraft."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.post('/admin/aircraft/add', data={
        'registration': 'N54321',
        'make': 'Cessna',
        'model': '172',
        'year': '2020',
        'status': 'available',
        'rate_per_hour': '150.00'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Aircraft added successfully' in response.data

    aircraft = Aircraft.query.filter_by(registration='N54321').first()
    assert aircraft is not None
    assert aircraft.make == 'Cessna'
    assert aircraft.model == '172'
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
    
    response = client.post('/admin/user/create?type=instructor', data={
        'email': 'new_instructor@example.com',
        'first_name': 'New',
        'last_name': 'Instructor',
        'phone': '123-456-7890',
        'certificates': 'CFI',
        'status': 'active'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'User created successfully' in response.data

def test_add_student(client, test_admin, session):
    """Test adding a new student."""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_admin.id
        sess['_fresh'] = True
    
    response = client.post('/admin/user/create?type=student', data={
        'email': 'new_student@example.com',
        'first_name': 'New',
        'last_name': 'Student',
        'phone': '123-456-7890',
        'student_id': 'S12345',
        'status': 'active'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'User created successfully' in response.data

def test_add_instructor_duplicate_email(client, test_instructor):
    response = client.post('/admin/user/create?type=instructor', data={
        'email': test_instructor.email,  # Using existing instructor's email
        'first_name': 'New',
        'last_name': 'Instructor',
        'phone': '123-456-7890',
        'certificates': 'CFI',
        'status': 'active'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Error creating user: Email already registered' in response.data

def test_edit_instructor(client, test_admin, test_instructor, session):
    """Test editing an instructor."""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_admin.id
        sess['_fresh'] = True
    
    response = client.post(f'/admin/user/{test_instructor.id}/edit', data={
        'email': 'updated_instructor@example.com',
        'first_name': 'Updated',
        'last_name': 'Instructor',
        'phone': '123-456-7890',
        'certificates': 'CFI, CFII',
        'status': 'active'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'User updated successfully' in response.data

def test_edit_instructor_invalid_data(client, test_instructor):
    response = client.post(f'/admin/user/{test_instructor.id}/edit', data={
        'email': 'invalid_email',
        'first_name': 'Updated',
        'last_name': 'Instructor',
        'phone': '123-456-7890',
        'certificates': 'CFI',
        'status': 'active'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Error updating user: Invalid email address' in response.data

def test_edit_instructor_nonexistent(client, test_admin, session):
    """Test editing a nonexistent instructor."""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_admin.id
        sess['_fresh'] = True
    
    response = client.post('/admin/user/999/edit', data={
        'email': 'updated_instructor@example.com',
        'first_name': 'Updated',
        'last_name': 'Instructor',
        'phone': '123-456-7890',
        'certificates': 'CFI',
        'status': 'active'
    }, follow_redirects=True)
    assert response.status_code == 404

def test_instructor_status_invalid(client, test_instructor):
    response = client.post(f'/admin/user/{test_instructor.id}/edit', data={
        'email': 'instructor@example.com',
        'first_name': 'Test',
        'last_name': 'Instructor',
        'phone': '123-456-7890',
        'certificates': 'CFI',
        'status': 'invalid_status'  # Invalid status value
    }, follow_redirects=True)
    assert response.status_code == 400
    assert b'Invalid status value' in response.data

def test_delete_aircraft(client, test_admin, test_aircraft, app):
    """Test deleting an aircraft."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.delete(f'/admin/aircraft/{test_aircraft.id}')
    assert response.status_code == 200

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
    
    response = client.delete(f'/admin/user/{test_instructor.id}')
    assert response.status_code == 200

def test_delete_instructor_unauthorized(client, test_user, test_instructor, session):
    """Test unauthorized deletion of an instructor."""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_user.id
        sess['_fresh'] = True
    
    response = client.delete(f'/admin/user/{test_instructor.id}')
    assert response.status_code == 200

def test_delete_instructor_nonexistent(client, test_admin, session):
    """Test deleting a nonexistent instructor."""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_admin.id
        sess['_fresh'] = True
    
    response = client.delete('/admin/user/999')
    assert response.status_code == 404

def test_edit_student(client, test_admin, test_user, session):
    """Test editing a student."""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_admin.id
        sess['_fresh'] = True
    
    response = client.post(f'/admin/user/{test_user.id}/edit', data={
        'email': 'updated_student@example.com',
        'first_name': 'Updated',
        'last_name': 'Student',
        'phone': '123-456-7890',
        'student_id': 'S54321',
        'status': 'active'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'User updated successfully' in response.data

def test_delete_student(client, test_admin, test_user, session):
    """Test deleting a student."""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_admin.id
        sess['_fresh'] = True
    
    response = client.delete(f'/admin/user/{test_user.id}')
    assert response.status_code == 200

def test_user_status_management(client, test_admin, test_user, session):
    """Test managing user status."""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_admin.id
        sess['_fresh'] = True
    
    # Deactivate user
    response = client.put(f'/admin/user/{test_user.id}/status',
        json={'status': 'inactive'},
        headers={'Content-Type': 'application/json'}
    )
    assert response.status_code == 200
    assert response.json['message'] == 'Status updated successfully'
    
    # Reactivate user
    response = client.put(f'/admin/user/{test_user.id}/status',
        json={'status': 'active'},
        headers={'Content-Type': 'application/json'}
    )
    assert response.status_code == 200
    assert b'User status updated successfully' in response.data

def test_user_status_invalid(client, test_user):
    response = client.post(f'/admin/user/{test_user.id}/edit', data={
        'email': 'user@example.com',
        'first_name': 'Test',
        'last_name': 'User',
        'phone': '123-456-7890',
        'status': 'invalid_status'  # Invalid status value
    }, follow_redirects=True)
    assert response.status_code == 400
    assert b'Invalid status value' in response.data 