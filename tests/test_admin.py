import pytest
from datetime import datetime, timedelta, UTC
from app.models import (
    User, Aircraft, Booking, MaintenanceType, MaintenanceRecord, Squawk,
    WeatherMinima, FlightLog, Endorsement, Document, AuditLog, WaitlistEntry,
    RecurringBooking
)
from app import db


def test_admin_dashboard_access(client, admin_user, app):
    """Test admin dashboard access."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = admin_user.id
            sess['_fresh'] = True

    response = client.get('/admin/dashboard')
    assert response.status_code == 200
    assert b'Admin Dashboard' in response.data


def test_admin_required_decorator(client, test_user, app):
    """Test admin required decorator."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_user.id
            sess['_fresh'] = True

    response = client.get('/admin/dashboard')
    assert response.status_code == 403
    assert b'Admin access required' in response.data


def test_manage_weather_minima(client, admin_user, app):
    """Test managing weather minima."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = admin_user.id
            sess['_fresh'] = True

        # Create weather minima
        response = client.post('/admin/weather-minima', json={
            'category': 'VFR',
            'ceiling_min': 3000,
            'visibility_min': 5.0,
            'wind_max': 25,
            'crosswind_max': 15
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Weather minima created successfully'

        # Get weather minima
        response = client.get('/admin/weather-minima')
        assert response.status_code == 200
        assert b'VFR' in response.data

        # Update weather minima
        minima = WeatherMinima.query.first()
        response = client.put(f'/admin/weather-minima/{minima.id}', json={
            'ceiling_min': 2500
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Weather minima updated successfully'

        # Delete weather minima
        response = client.delete(f'/admin/weather-minima/{minima.id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Weather minima deleted successfully'


def test_manage_endorsements(
        client,
        admin_user,
        test_user,
        test_instructor,
        app):
    """Test managing endorsements."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = admin_user.id
            sess['_fresh'] = True

        # Create endorsement
        endorsement = Endorsement(
            student=test_user,
            instructor=test_instructor,
            type='solo',
            description='Solo endorsement for pattern work',
            expiration=datetime.now(UTC) + timedelta(days=90)
        )
        db.session.add(endorsement)
        db.session.commit()

        # View endorsements
        response = client.get('/admin/endorsements')
        assert response.status_code == 200
        assert b'solo' in response.data

        # Update endorsement
        response = client.put(f'/admin/endorsements/{endorsement.id}', json={
            'expiration': (datetime.now(UTC) + timedelta(days=180)).isoformat()
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Endorsement updated successfully'

        # Delete endorsement
        response = client.delete(f'/admin/endorsements/{endorsement.id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Endorsement deleted successfully'


def test_manage_documents(client, admin_user, test_user, app):
    """Test managing documents."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = admin_user.id
            sess['_fresh'] = True

        # Create document
        document = Document(
            user=test_user,
            type='medical',
            filename='medical_certificate.pdf',
            url='https://example.com/documents/medical.pdf',
            expiration=datetime.now(UTC) + timedelta(days=365)
        )
        db.session.add(document)
        db.session.commit()

        # View documents
        response = client.get('/admin/documents')
        assert response.status_code == 200
        assert b'medical_certificate.pdf' in response.data

        # Update document
        response = client.put(f'/admin/documents/{document.id}', json={
            'expiration': (datetime.now(UTC) + timedelta(days=730)).isoformat()
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Document updated successfully'

        # Delete document
        response = client.delete(f'/admin/documents/{document.id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Document deleted successfully'


def test_manage_waitlist(
        client,
        admin_user,
        test_user,
        test_aircraft,
        test_instructor,
        app):
    """Test managing waitlist entries."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = admin_user.id
            sess['_fresh'] = True

        # Create waitlist entry
        entry = WaitlistEntry(
            student=test_user,
            instructor=test_instructor,
            aircraft=test_aircraft,
            requested_date=datetime.now(UTC) + timedelta(days=7),
            time_preference='afternoon',
            duration_hours=2.0,
            status='active'
        )
        db.session.add(entry)
        db.session.commit()

        # View waitlist
        response = client.get('/admin/waitlist')
        assert response.status_code == 200
        assert b'afternoon' in response.data

        # Update waitlist entry
        response = client.put(f'/admin/waitlist/{entry.id}', json={
            'status': 'fulfilled'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Waitlist entry updated successfully'


def test_manage_recurring_bookings(
        client,
        admin_user,
        test_user,
        test_aircraft,
        test_instructor,
        app):
    """Test managing recurring bookings."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = admin_user.id
            sess['_fresh'] = True

        # Create recurring booking
        booking = RecurringBooking(
            student=test_user,
            instructor=test_instructor,
            aircraft=test_aircraft,
            day_of_week=2,  # Wednesday
            start_time=datetime.strptime('14:00', '%H:%M').time(),
            duration_hours=2.0,
            start_date=datetime.now(UTC),
            end_date=datetime.now(UTC) + timedelta(days=90),
            status='active'
        )
        db.session.add(booking)
        db.session.commit()

        # View recurring bookings
        response = client.get('/admin/recurring-bookings')
        assert response.status_code == 200
        assert b'Wednesday' in response.data

        # Update recurring booking
        response = client.put(f'/admin/recurring-bookings/{booking.id}', json={
            'status': 'inactive'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Recurring booking updated successfully'

        # Delete recurring booking
        response = client.delete(f'/admin/recurring-bookings/{booking.id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Recurring booking deleted successfully'


def test_view_audit_logs(client, admin_user, app):
    """Test viewing audit logs."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = admin_user.id
            sess['_fresh'] = True

        # Create audit log
        log = AuditLog(
            user=admin_user,
            action='update',
            table_name='aircraft',
            record_id=1,
            changes={
                'status': ['available', 'maintenance'],
                'maintenance_status': ['airworthy', 'maintenance_due']
            }
        )
        db.session.add(log)
        db.session.commit()

        # View audit logs
        response = client.get('/admin/audit-logs')
        assert response.status_code == 200
        assert b'update' in response.data
        assert b'aircraft' in response.data


def test_manage_flight_logs(
        client,
        admin_user,
        test_user,
        test_booking,
        test_instructor,
        app):
    """Test managing flight logs."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = admin_user.id
            sess['_fresh'] = True

        # Create flight log
        log = FlightLog(
            booking=test_booking,
            pic=test_instructor,
            sic=test_user,
            flight_date=datetime.now(UTC),
            route='KPAO KHWD KPAO',
            weather_conditions='VFR',
            ground_instruction=0.5,
            dual_received=2.0,
            pic_time=2.0,
            landings_day=8
        )
        db.session.add(log)
        db.session.commit()

        # View flight logs
        response = client.get('/admin/flight-logs')
        assert response.status_code == 200
        assert b'KPAO KHWD KPAO' in response.data

        # Update flight log
        response = client.put(f'/admin/flight-logs/{log.id}', json={
            'landings_day': 10
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Flight log updated successfully'

        # Delete flight log
        response = client.delete(f'/admin/flight-logs/{log.id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Flight log deleted successfully'
