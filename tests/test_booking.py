import pytest
from datetime import datetime, timedelta, UTC, time
from app.models import (
    User, Aircraft, Booking, CheckIn, CheckOut, Invoice, WeatherMinima,
    FlightLog, WaitlistEntry, RecurringBooking
)
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
    assert b'Booking Dashboard' in response.data
    assert b'Book a Flight' in response.data


def test_create_booking(
        client,
        test_user,
        test_aircraft,
        test_instructor,
        app,
        session):
    """Test creating a new booking."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_user.id
            sess['_fresh'] = True

        start_time = datetime.now(UTC) + timedelta(days=1)
        response = client.post('/bookings', json={
            'start_time': start_time.strftime('%Y-%m-%dT%H:%M'),
            'duration': '1',
            'aircraft_id': str(test_aircraft.id),
            'instructor_id': str(test_instructor.id)
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['message'] == 'Booking created successfully'
        assert 'booking_id' in data


def test_create_booking_with_weather(client, test_user, test_aircraft, app):
    """Test creating a booking with weather briefing."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_user.id
            sess['_fresh'] = True

        # Create weather minima
        minima = WeatherMinima(
            category='VFR',
            ceiling_min=3000,
            visibility_min=5.0,
            wind_max=25,
            crosswind_max=15
        )
        db.session.add(minima)
        db.session.commit()

        start_time = datetime.now(UTC) + timedelta(days=1)
        response = client.post('/bookings', json={
            'start_time': start_time.strftime('%Y-%m-%dT%H:%M'),
            'duration': '1',
            'aircraft_id': str(test_aircraft.id),
            'weather_briefing': {
                'metar': 'KPAO 191400Z 27010KT 10SM FEW020 18/12 A3001',
                'taf': 'KPAO 191400Z 1914/2014 27012KT P6SM FEW020'
            }
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['message'] == 'Booking created successfully'
        assert 'booking_id' in data

        # Verify weather briefing was saved
        booking = Booking.query.get(data['booking_id'])
        assert booking.weather_briefing is not None
        assert 'metar' in booking.weather_briefing
        assert 'taf' in booking.weather_briefing


def test_cancel_booking_with_reason(client, test_user, test_aircraft, app):
    """Test canceling a booking with a specific reason."""
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

        # Cancel the booking with weather reason
        response = client.post(f'/bookings/{booking.id}/cancel', json={
            'reason': 'weather',
            'notes': 'IFR conditions below minimums'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Booking cancelled successfully'

        # Verify booking was updated
        booking = Booking.query.get(booking.id)
        assert booking.status == 'cancelled'
        assert booking.cancellation_reason == 'weather'
        assert booking.cancellation_notes == 'IFR conditions below minimums'


def test_check_in_with_flight_log(
        client,
        test_user,
        test_aircraft,
        test_instructor,
        app):
    """Test check-in process with flight logging."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_instructor.id
            sess['_fresh'] = True

        # Create a booking
        booking = Booking(
            student_id=test_user.id,
            instructor_id=test_instructor.id,
            aircraft_id=test_aircraft.id,
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC) + timedelta(hours=1),
            status='confirmed'
        )
        db.session.add(booking)
        db.session.commit()

        # Perform check-in
        response = client.post(f'/bookings/{booking.id}/checkin', json={
            'hobbs_start': 1234.5,
            'tach_start': 2345.6,
            'notes': 'Pre-flight inspection completed'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Check-in recorded successfully'
        assert 'check_in_id' in data

        # Verify check-in record
        check_in = CheckIn.query.get(data['check_in_id'])
        assert check_in is not None
        assert check_in.hobbs_start == 1234.5
        assert check_in.tach_start == 2345.6
        assert check_in.notes == 'Pre-flight inspection completed'

        # Verify booking status
        booking = Booking.query.get(booking.id)
        assert booking.status == 'in_progress'


def test_check_out_with_flight_log(
        client,
        test_user,
        test_aircraft,
        test_instructor,
        app):
    """Test check-out process with flight logging."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_instructor.id
            sess['_fresh'] = True

        # Create a booking and check-in
        booking = Booking(
            student_id=test_user.id,
            instructor_id=test_instructor.id,
            aircraft_id=test_aircraft.id,
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC) + timedelta(hours=1),
            status='in_progress'
        )
        db.session.add(booking)
        db.session.commit()

        check_in = CheckIn(
            booking=booking,
            aircraft=test_aircraft,
            instructor=test_instructor,
            hobbs_start=1234.5,
            tach_start=2345.6,
            instructor_start_time=datetime.now(UTC)
        )
        db.session.add(check_in)
        db.session.commit()

        # Perform check-out with flight log
        response = client.post(f'/bookings/{booking.id}/checkout', json={
            'hobbs_end': 1236.2,
            'tach_end': 2347.1,
            'notes': 'Flight completed successfully',
            'flight_log': {
                'route': 'KPAO KHWD KPAO',
                'remarks': 'Pattern work and landings',
                'weather_conditions': 'VFR',
                'ground_instruction': 0.5,
                'dual_received': 2.0,
                'pic_time': 2.0,
                'cross_country': 0.0,
                'night': 0.0,
                'actual_instrument': 0.0,
                'simulated_instrument': 0.0,
                'landings_day': 8,
                'landings_night': 0
            }
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Check-out recorded successfully'
        assert 'check_out_id' in data

        # Verify check-out record
        check_out = CheckOut.query.get(data['check_out_id'])
        assert check_out is not None
        assert check_out.hobbs_end == 1236.2
        assert check_out.tach_end == 2347.1
        assert check_out.total_aircraft_time == pytest.approx(1.7)

        # Verify flight log
        flight_log = FlightLog.query.filter_by(booking_id=booking.id).first()
        assert flight_log is not None
        assert flight_log.route == 'KPAO KHWD KPAO'
        assert flight_log.weather_conditions == 'VFR'
        assert flight_log.ground_instruction == 0.5
        assert flight_log.dual_received == 2.0
        assert flight_log.landings_day == 8


def test_create_recurring_booking(
        client,
        test_user,
        test_aircraft,
        test_instructor,
        app):
    """Test creating a recurring booking."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_user.id
            sess['_fresh'] = True

        response = client.post('/bookings/recurring', json={
            'aircraft_id': test_aircraft.id,
            'instructor_id': test_instructor.id,
            'day_of_week': 2,  # Wednesday
            'start_time': '14:00',
            'duration_hours': 2.0,
            'start_date': datetime.now(UTC).strftime('%Y-%m-%d'),
            'end_date': (datetime.now(UTC) + timedelta(days=90)).strftime('%Y-%m-%d')
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Recurring booking created successfully'
        assert 'recurring_id' in data

        # Verify recurring booking
        booking = RecurringBooking.query.get(data['recurring_id'])
        assert booking is not None
        assert booking.day_of_week == 2
        assert booking.start_time == time(14, 0)
        assert booking.duration_hours == 2.0
        assert booking.status == 'active'


def test_join_waitlist(client, test_user, test_aircraft, test_instructor, app):
    """Test joining the waitlist."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_user.id
            sess['_fresh'] = True

        response = client.post(
            '/bookings/waitlist',
            json={
                'aircraft_id': test_aircraft.id,
                'instructor_id': test_instructor.id,
                'requested_date': (
                    datetime.now(UTC) +
                    timedelta(
                        days=7)).strftime('%Y-%m-%d'),
                'time_preference': 'afternoon',
                'duration_hours': 2.0})
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Added to waitlist successfully'
        assert 'waitlist_id' in data

        # Verify waitlist entry
        entry = WaitlistEntry.query.get(data['waitlist_id'])
        assert entry is not None
        assert entry.time_preference == 'afternoon'
        assert entry.duration_hours == 2.0
        assert entry.status == 'active'


def test_get_weather_briefing(client, test_user, test_booking, app):
    """Test getting weather briefing for a booking."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_user.id
            sess['_fresh'] = True

        # Add weather briefing to booking
        test_booking.weather_briefing = {
            'metar': 'KPAO 191400Z 27010KT 10SM FEW020 18/12 A3001',
            'taf': 'KPAO 191400Z 1914/2014 27012KT P6SM FEW020'
        }
        db.session.commit()

        response = client.get(f'/bookings/{test_booking.id}/weather')
        assert response.status_code == 200
        data = response.get_json()
        assert 'metar' in data
        assert 'taf' in data


def test_get_weather_minima(client, test_user, app):
    """Test getting weather minima."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_user.id
            sess['_fresh'] = True

        # Create weather minima
        minima = WeatherMinima(
            category='VFR',
            ceiling_min=3000,
            visibility_min=5.0,
            wind_max=25,
            crosswind_max=15
        )
        db.session.add(minima)
        db.session.commit()

        response = client.get('/bookings/weather-minima')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]['category'] == 'VFR'
        assert data[0]['ceiling_min'] == 3000
        assert data[0]['visibility_min'] == 5.0
