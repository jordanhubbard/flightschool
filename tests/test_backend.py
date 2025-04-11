from flask_login import current_user
from datetime import datetime, timedelta, UTC
from flask import session
from app.models import User, Aircraft, Booking
from app import db
import pytest

def test_instructor_management(client, test_admin, app):
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.post('/admin/instructor/create', data={
        'email': 'new.instructor@example.com',
        'first_name': 'New',
        'last_name': 'Instructor',
        'phone': '123-456-7890',
        'certificates': 'CFI',
        'status': 'active'
    }, follow_redirects=True)
    assert b'Instructor created successfully' in response.data

def test_google_calendar_settings(client, test_admin, app):
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.get('/admin/calendar/settings')
    assert response.status_code == 200
    assert b'Calendar Settings' in response.data

def test_google_calendar_oauth(client, test_admin, app):
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.get('/admin/calendar/oauth')
    assert response.status_code == 302
    assert 'accounts.google.com' in response.location

def test_booking_management(client, test_user, test_aircraft, app):
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_user.id
            sess['_fresh'] = True
        
        # Create a booking
        booking = Booking(
            student_id=test_user.id,
            aircraft_id=test_aircraft.id,
            instructor_id=None,
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
            status='pending'
        )
        db.session.add(booking)
        db.session.commit()
        db.session.refresh(booking)
    
        # Test viewing the booking within the app context
        response = client.get(f'/booking/{booking.id}')
        assert response.status_code == 200
        assert test_aircraft.registration.encode() in response.data
        assert b'Pending' in response.data

def test_booking_cancellation(client, test_user, test_aircraft, app):
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_user.id
            sess['_fresh'] = True
        
        # Create a booking
        booking = Booking(
            student_id=test_user.id,
            aircraft_id=test_aircraft.id,
            instructor_id=None,
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
            status='pending'
        )
        db.session.add(booking)
        db.session.commit()
        db.session.refresh(booking)
    
        # Test canceling the booking within the app context
        response = client.post(f'/booking/{booking.id}/cancel')
        assert response.status_code == 200
        assert b'Booking cancelled successfully' in response.data

def test_user_management(client, test_admin, app):
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_admin.id
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
    assert b'User created successfully' in response.data

def test_aircraft_management(client, test_admin, app):
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.post('/admin/aircraft/create', data={
        'registration': 'N54321',
        'make_model': 'Piper Cherokee',
        'year': '2019',
        'status': 'active'
    }, follow_redirects=True)
    assert b'Aircraft created successfully' in response.data

def test_schedule_management(client, test_admin, app):
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.get('/admin/schedule')
    assert response.status_code == 200
    assert b'Schedule Management' in response.data

def test_report_generation(client, test_admin, app):
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.get('/admin/reports')
    assert response.status_code == 200
    assert b'Report Generation' in response.data

def test_system_settings(client, test_admin, app):
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.get('/admin/settings')
    assert response.status_code == 200
    assert b'System Settings' in response.data 