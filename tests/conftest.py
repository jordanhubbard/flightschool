import os
import tempfile
import pytest
from datetime import datetime, timedelta, UTC
from app import create_app, db
from app.models import User, Aircraft, Booking, MaintenanceType, MaintenanceRecord, Squawk, CheckIn, CheckOut, Invoice
from flask import session
from flask_login import LoginManager, login_user
from sqlalchemy.orm import scoped_session

@pytest.fixture(scope='function')
def app():
    """Create and configure a new app instance for each test."""
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'WTF_CSRF_CHECK_DEFAULT': False,
        'SECRET_KEY': 'test-key',
        'LOGIN_DISABLED': True  # Disable login requirement for testing
    })

    # Create the database and the database tables
    with app.app_context():
        # Import all models to ensure they are registered
        from app.models import User, Aircraft, Booking, MaintenanceType, MaintenanceRecord, Squawk, CheckIn, CheckOut, Invoice
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

@pytest.fixture
def test_user(app):
    """Create a test user."""
    with app.app_context():
        user = User(
            email='test@example.com',
            first_name='Test',
            last_name='User',
            role='student',
            is_admin=False,
            is_instructor=False,
            status='active'
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)  # Refresh the instance to ensure it's bound to the session
        yield user
        db.session.rollback()

@pytest.fixture
def test_admin(app):
    """Create a test admin user."""
    with app.app_context():
        admin = User(
            email='admin@example.com',
            first_name='Admin',
            last_name='User',
            role='admin',
            is_admin=True,
            is_instructor=False,
            status='active'
        )
        admin.set_password('password123')
        db.session.add(admin)
        db.session.commit()
        db.session.refresh(admin)  # Refresh the instance to ensure it's bound to the session
        yield admin
        db.session.rollback()

@pytest.fixture
def test_instructor(app):
    """Create a test instructor user."""
    with app.app_context():
        instructor = User(
            email='instructor@example.com',
            first_name='John',
            last_name='Doe',
            phone='123-456-7890',
            certificates='CFI, CFII',
            role='instructor',
            is_admin=False,
            is_instructor=True,
            status='active',
            instructor_rate_per_hour=75.00
        )
        instructor.set_password('password123')
        db.session.add(instructor)
        db.session.commit()
        db.session.refresh(instructor)  # Refresh the instance to ensure it's bound to the session
        yield instructor
        db.session.rollback()

@pytest.fixture
def test_aircraft(app):
    """Create a test aircraft."""
    with app.app_context():
        aircraft = Aircraft(
            registration='N12345',
            make_model='Cessna 172',
            year=2020,
            status='available',
            rate_per_hour=150.00
        )
        db.session.add(aircraft)
        db.session.commit()
        db.session.refresh(aircraft)  # Refresh the instance to ensure it's bound to the session
        yield aircraft
        db.session.rollback()

@pytest.fixture
def test_booking(app, test_user, test_aircraft, test_instructor):
    """Create a test booking."""
    with app.app_context():
        booking = Booking(
            student_id=test_user.id,
            instructor_id=test_instructor.id,
            aircraft_id=test_aircraft.id,
            start_time=datetime.now(UTC) + timedelta(days=1),
            end_time=datetime.now(UTC) + timedelta(days=1, hours=2),
            status='confirmed'
        )
        db.session.add(booking)
        db.session.commit()
        db.session.refresh(booking)  # Refresh the instance to ensure it's bound to the session
        yield booking
        db.session.rollback()

@pytest.fixture
def test_check_in(app, test_booking):
    """Create a test check-in."""
    with app.app_context():
        check_in = CheckIn(
            booking_id=test_booking.id,
            aircraft_id=test_booking.aircraft_id,
            instructor_id=test_booking.instructor_id,
            hobbs_start=1234.5,
            tach_start=2345.6,
            instructor_start_time=datetime.now(UTC),
            notes='Pre-flight inspection completed'
        )
        db.session.add(check_in)
        db.session.commit()
        db.session.refresh(check_in)  # Refresh the instance to ensure it's bound to the session
        yield check_in
        db.session.rollback()

@pytest.fixture
def test_check_out(app, test_booking, test_check_in):
    """Create a test check-out."""
    with app.app_context():
        check_out = CheckOut(
            booking_id=test_booking.id,
            aircraft_id=test_booking.aircraft_id,
            instructor_id=test_booking.instructor_id,
            hobbs_end=1236.5,
            tach_end=2347.6,
            instructor_end_time=datetime.now(UTC) + timedelta(hours=2),
            notes='Post-flight inspection completed'
        )
        db.session.add(check_out)
        db.session.commit()
        db.session.refresh(check_out)  # Refresh the instance to ensure it's bound to the session
        yield check_out
        db.session.rollback()

@pytest.fixture
def test_invoice(app, test_booking, test_check_out):
    """Create a test invoice."""
    with app.app_context():
        invoice = Invoice(
            booking_id=test_booking.id,
            aircraft_id=test_booking.aircraft_id,
            student_id=test_booking.student_id,
            invoice_number=f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}-{test_booking.id}",
            aircraft_rate=150.00,
            instructor_rate=75.00,
            aircraft_time=2.0,
            instructor_time=2.0,
            status='pending'
        )
        db.session.add(invoice)
        db.session.commit()
        db.session.refresh(invoice)  # Refresh the instance to ensure it's bound to the session
        yield invoice
        db.session.rollback()

@pytest.fixture
def auth(client):
    """Authentication helper class."""
    class AuthActions:
        def __init__(self, client):
            self._client = client

        def login(self, email='test@example.com', password='password123'):
            return self._client.post(
                '/auth/login',
                data={'email': email, 'password': password}
            )

        def logout(self):
            return self._client.get('/auth/logout')

    return AuthActions(client)

@pytest.fixture
def logged_in_user(client, test_user, app):
    """Log in a test user."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.id
            sess['_fresh'] = True
            sess['csrf_token'] = 'test-token'
        login_user(test_user)
        db.session.refresh(test_user)  # Refresh the instance to ensure it's bound to the session
        yield test_user
        db.session.rollback()

@pytest.fixture
def logged_in_admin(client, test_admin, app):
    """Log in a test admin user."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
            sess['csrf_token'] = 'test-token'
        login_user(test_admin)
        db.session.refresh(test_admin)  # Refresh the instance to ensure it's bound to the session
        yield test_admin
        db.session.rollback()

@pytest.fixture
def logged_in_instructor(client, test_instructor, app):
    """Log in a test instructor user."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_instructor.id
            sess['_fresh'] = True
            sess['csrf_token'] = 'test-token'
        login_user(test_instructor)
        db.session.refresh(test_instructor)  # Refresh the instance to ensure it's bound to the session
        yield test_instructor
        db.session.rollback()
