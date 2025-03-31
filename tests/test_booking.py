import pytest
from app.models import User, Aircraft, Booking
from datetime import datetime, timedelta
from flask import session
from app import db

def test_booking_dashboard_access(client, test_user, app):
    """Test access to booking dashboard."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.id
            sess['_fresh'] = True
    
    response = client.get('/booking/dashboard')
    assert response.status_code == 200
    assert b'Book a Flight' in response.data

def test_create_booking(client, test_user, test_aircraft, test_instructor, app):
    """Test creating a new booking."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.id
            sess['_fresh'] = True
    
    # First get the form to get the CSRF token
    response = client.get('/booking/create')
    assert response.status_code == 200
    
    start_time = datetime.now() + timedelta(days=1)
    response = client.post('/booking/create', data={
        'start_time': start_time.strftime('%Y-%m-%dT%H:%M'),
        'duration': '1',
        'aircraft_id': str(test_aircraft.id),
        'instructor_id': str(test_instructor.id)
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Booking created successfully' in response.data

def test_create_booking_without_instructor(client, test_user, test_aircraft, app):
    """Test creating a booking without an instructor."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.id
            sess['_fresh'] = True
    
    # First get the form to get the CSRF token
    response = client.get('/booking/create')
    assert response.status_code == 200
    
    start_time = datetime.now() + timedelta(days=1)
    response = client.post('/booking/create', data={
        'start_time': start_time.strftime('%Y-%m-%dT%H:%M'),
        'duration': '1',
        'aircraft_id': str(test_aircraft.id)
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Booking created successfully' in response.data

def test_create_booking_conflict(client, test_user, test_aircraft, app):
    """Test creating a booking with a time conflict."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.id
            sess['_fresh'] = True
    
    # First get the form to get the CSRF token
    response = client.get('/booking/create')
    assert response.status_code == 200
    
    start_time = datetime.now() + timedelta(days=1)
    
    # Create first booking
    response = client.post('/booking/create', data={
        'start_time': start_time.strftime('%Y-%m-%dT%H:%M'),
        'duration': '1',
        'aircraft_id': str(test_aircraft.id)
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Booking created successfully' in response.data
    
    # Try to create second booking at same time
    response = client.post('/booking/create', data={
        'start_time': start_time.strftime('%Y-%m-%dT%H:%M'),
        'duration': '1',
        'aircraft_id': str(test_aircraft.id)
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Time slot is not available' in response.data

def test_cancel_booking(client, test_user, test_aircraft, app):
    """Test canceling a booking."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.id
            sess['_fresh'] = True
        
        # Create a booking first
        booking = Booking(
            student_id=test_user.id,
            aircraft_id=test_aircraft.id,
            start_time=datetime.now() + timedelta(days=1),
            end_time=datetime.now() + timedelta(days=1, hours=1),
            status='confirmed'
        )
        db.session.add(booking)
        db.session.commit()
        db.session.refresh(booking)
    
    # Cancel the booking
    response = client.post(f'/booking/{booking.id}/cancel', follow_redirects=True)
    assert response.status_code == 200
    assert b'Booking cancelled successfully' in response.data

def test_view_bookings(client, test_user, test_aircraft, app):
    """Test viewing list of bookings."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.id
            sess['_fresh'] = True
        
        # Create a booking first
        booking = Booking(
            student_id=test_user.id,
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
    assert test_aircraft.registration.encode() in response.data
    assert b'Confirmed' in response.data 