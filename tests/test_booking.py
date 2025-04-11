import pytest
from datetime import datetime, timedelta, UTC
from app.models import User, Aircraft, Booking, CheckIn, CheckOut, Invoice
from flask import session
from app import db

def test_booking_dashboard_access(client, test_user, app):
    """Test access to booking dashboard."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_user.id
            sess['_fresh'] = True
    
    response = client.get('/dashboard')
    assert response.status_code == 200
    assert b'Book a Flight' in response.data

def test_create_booking(client, test_user, test_aircraft, test_instructor, app, session):
    """Test creating a new booking."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_user.id
            sess['_fresh'] = True

        start_time = datetime.now(UTC) + timedelta(days=1)
        response = client.post('/book', data={
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
            sess['_user_id'] = test_user.id
            sess['_fresh'] = True
    
    start_time = datetime.now(UTC) + timedelta(days=1)
    response = client.post('/book', data={
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
            sess['_user_id'] = test_user.id
            sess['_fresh'] = True
    
    start_time = datetime.now(UTC) + timedelta(days=1)
    
    # Create first booking
    response = client.post('/book', data={
        'start_time': start_time.strftime('%Y-%m-%dT%H:%M'),
        'duration': '1',
        'aircraft_id': str(test_aircraft.id)
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Booking created successfully' in response.data
    
    # Try to create second booking at same time
    response = client.post('/book', data={
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
            sess['_user_id'] = test_user.id
            sess['_fresh'] = True
        
        # Create a booking first
        booking = Booking(
            student_id=test_user.id,
            aircraft_id=test_aircraft.id,
            start_time=datetime.now(UTC) + timedelta(days=1),
            end_time=datetime.now(UTC) + timedelta(days=1, hours=1),
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
            sess['_user_id'] = test_user.id
            sess['_fresh'] = True
        
        # Create a booking first
        booking = Booking(
            student_id=test_user.id,
            aircraft_id=test_aircraft.id,
            start_time=datetime.now(UTC) + timedelta(days=1),
            end_time=datetime.now(UTC) + timedelta(days=1, hours=1),
            status='confirmed'
        )
        db.session.add(booking)
        db.session.commit()
        db.session.refresh(booking)
    
    response = client.get('/list')
    assert response.status_code == 200
    assert test_aircraft.registration.encode() in response.data
    assert b'Confirmed' in response.data

def test_check_in_booking(client, test_booking, test_user):
    """Test checking in for a booking."""
    client.post('/auth/login', data={
        'email': test_user.email,
        'password': 'password123'
    })

    test_booking.status = 'confirmed'
    db.session.commit()

    response = client.post(f'/check-in/{test_booking.id}', data={
        'hobbs_start': '1234.5',
        'tach_start': '2345.6',
        'instructor_start_time': datetime.now(UTC).strftime('%Y-%m-%dT%H:%M'),
        'notes': 'Pre-flight inspection completed'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Check-in completed successfully' in response.data

    check_in = CheckIn.query.filter_by(booking_id=test_booking.id).first()
    assert check_in is not None
    assert check_in.hobbs_start == 1234.5
    assert check_in.tach_start == 2345.6
    assert check_in.notes == 'Pre-flight inspection completed'

    # Verify the booking status was updated
    booking = Booking.query.get(test_booking.id)
    assert booking.status == 'in_progress'

def test_check_out_booking(client, test_booking, test_check_in, test_user):
    """Test checking out from a booking."""
    client.post('/auth/login', data={
        'email': test_user.email,
        'password': 'password123'
    })

    test_booking.status = 'in_progress'
    db.session.commit()

    response = client.post(f'/check-out/{test_booking.id}', data={
        'hobbs_end': '1236.2',
        'tach_end': '2347.1',
        'instructor_end_time': datetime.now(UTC).strftime('%Y-%m-%dT%H:%M'),
        'notes': 'Touch and go practice completed'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Check-out completed successfully' in response.data

    check_out = CheckOut.query.filter_by(booking_id=test_booking.id).first()
    assert check_out is not None
    assert check_out.hobbs_end == 1236.2
    assert check_out.tach_end == 2347.1
    assert check_out.total_aircraft_time == pytest.approx(1.7, rel=1e-2)
    assert check_out.notes == 'Touch and go practice completed'

    # Verify the booking status was updated
    booking = Booking.query.get(test_booking.id)
    assert booking.status == 'completed'
