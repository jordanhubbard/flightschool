import pytest
from datetime import datetime, timedelta
from app.models import Booking, db

def test_booking_dashboard_access(client, test_user):
    client.post('/login', data={
        'email': 'test@example.com',
        'password': 'password123'
    })
    response = client.get('/booking/dashboard')
    assert b'Book a Flight' in response.data

def test_create_booking(client, test_user, test_aircraft, test_instructor):
    client.post('/login', data={
        'email': 'test@example.com',
        'password': 'password123'
    })
    
    start_time = datetime.now() + timedelta(days=1)
    response = client.post('/booking/book', data={
        'start_time': start_time.strftime('%Y-%m-%dT%H:%M'),
        'duration': '1',
        'aircraft_id': str(test_aircraft.id),
        'instructor_id': str(test_instructor.id)
    }, follow_redirects=True)
    
    assert b'Booking created successfully' in response.data
    booking = Booking.query.filter_by(student_id=test_user.id).first()
    assert booking is not None
    assert booking.instructor_id == test_instructor.id

def test_create_booking_without_instructor(client, test_user, test_aircraft):
    client.post('/login', data={
        'email': 'test@example.com',
        'password': 'password123'
    })
    
    start_time = datetime.now() + timedelta(days=1)
    response = client.post('/booking/book', data={
        'start_time': start_time.strftime('%Y-%m-%dT%H:%M'),
        'duration': '1',
        'aircraft_id': str(test_aircraft.id)
    }, follow_redirects=True)
    
    assert b'Booking created successfully' in response.data
    booking = Booking.query.filter_by(student_id=test_user.id).first()
    assert booking is not None
    assert booking.instructor_id is None

def test_create_booking_conflict(client, test_user, test_aircraft):
    client.post('/login', data={
        'email': 'test@example.com',
        'password': 'password123'
    })
    
    start_time = datetime.now() + timedelta(days=1)
    
    # Create first booking
    response = client.post('/booking/book', data={
        'start_time': start_time.strftime('%Y-%m-%dT%H:%M'),
        'duration': '1',
        'aircraft_id': str(test_aircraft.id)
    }, follow_redirects=True)
    assert b'Booking created successfully' in response.data
    
    # Try to create conflicting booking
    response = client.post('/booking/book', data={
        'start_time': start_time.strftime('%Y-%m-%dT%H:%M'),
        'duration': '1',
        'aircraft_id': str(test_aircraft.id)
    }, follow_redirects=True)
    
    assert b'Aircraft is already booked' in response.data

def test_cancel_booking(client, test_user, test_aircraft):
    client.post('/login', data={
        'email': 'test@example.com',
        'password': 'password123'
    })
    
    # Create a booking
    start_time = datetime.now() + timedelta(days=1)
    response = client.post('/booking/book', data={
        'start_time': start_time.strftime('%Y-%m-%dT%H:%M'),
        'duration': '1',
        'aircraft_id': str(test_aircraft.id)
    }, follow_redirects=True)
    assert b'Booking created successfully' in response.data
    
    # Get the booking and cancel it
    booking = Booking.query.filter_by(student_id=test_user.id).first()
    db.session.refresh(booking)  # Refresh the session to avoid stale data
    
    response = client.post(f'/booking/booking/{booking.id}/cancel', follow_redirects=True)
    assert b'Booking cancelled successfully' in response.data 