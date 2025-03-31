import os
import tempfile
import pytest
from datetime import datetime, timedelta, UTC
from app import create_app, db
from app.models import User, Aircraft, Booking, MaintenanceType, MaintenanceRecord, Squawk, CheckIn, CheckOut, Invoice
from flask import session, current_app
from flask_login import LoginManager, login_user
from sqlalchemy.orm import scoped_session
import sqlalchemy as sa
from flask import Flask

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app('testing')
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
    app.config['SERVER_NAME'] = 'localhost'  # Required for url_for to work in tests
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    yield app
    
    # Clean up
    with app.app_context():
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def _db(app):
    """Create a new database for the test."""
    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='function')
def session(app, _db):
    """Create a new database session for a test."""
    with app.app_context():
        connection = _db.engine.connect()
        transaction = connection.begin()
        
        # Create a session bound to the connection
        session = _db.session.registry()
        session.bind = connection
        
        yield session
        
        session.close()
        transaction.rollback()
        connection.close()

@pytest.fixture(scope='function')
def runner(app):
    """Create a test CLI runner."""
    return app.test_cli_runner()

@pytest.fixture
def test_user(_db):
    """Create a test user."""
    with _db.session.begin():
        user = User(
            email=f'test_user_{datetime.now().timestamp()}@example.com',
            first_name='Test',
            last_name='User',
            role='student',
            status='active'
        )
        user.set_password('password123')
        _db.session.add(user)
        _db.session.commit()
        return user

@pytest.fixture
def test_instructor(_db):
    """Create a test instructor."""
    with _db.session.begin():
        instructor = User(
            email=f'test_instructor_{datetime.now().timestamp()}@example.com',
            first_name='Test',
            last_name='Instructor',
            role='instructor',
            status='active',
            is_instructor=True
        )
        instructor.set_password('password123')
        _db.session.add(instructor)
        _db.session.commit()
        return instructor

@pytest.fixture
def test_admin(_db):
    """Create a test admin user."""
    with _db.session.begin():
        admin = User(
            email=f'test_admin_{datetime.now().timestamp()}@example.com',
            first_name='Test',
            last_name='Admin',
            role='admin',
            status='active',
            is_admin=True
        )
        admin.set_password('password123')
        _db.session.add(admin)
        _db.session.commit()
        return admin

@pytest.fixture
def test_aircraft(_db):
    """Create a test aircraft."""
    with _db.session.begin():
        aircraft = Aircraft(
            registration=f'N1234{datetime.now().timestamp()}',
            make_model='Cessna 172',
            year=1965,
            status='available',
            rate_per_hour=175.00
        )
        _db.session.add(aircraft)
        _db.session.commit()
        return aircraft

@pytest.fixture
def auth_client(client, test_user, _db):
    """A test client with a logged-in user."""
    with client.session_transaction() as sess:
        sess['user_id'] = test_user.id
        sess['_fresh'] = True
    return client

@pytest.fixture
def admin_client(client, test_admin, _db):
    """A test client with a logged-in admin user."""
    with client.session_transaction() as sess:
        sess['user_id'] = test_admin.id
        sess['_fresh'] = True
    return client

@pytest.fixture(scope='function')
def test_booking(_db, test_user, test_instructor, test_aircraft):
    """Create a test booking."""
    with _db.session.begin():
        booking = Booking(
            student_id=test_user.id,
            instructor_id=test_instructor.id,
            aircraft_id=test_aircraft.id,
            start_time=datetime.now() + timedelta(days=1),
            end_time=datetime.now() + timedelta(days=1, hours=2),
            status='scheduled'
        )
        _db.session.add(booking)
        _db.session.commit()
        return booking

@pytest.fixture(scope='function')
def test_check_in(_db, test_booking):
    """Create a test check-in."""
    with _db.session.begin():
        check_in = CheckIn(
            booking_id=test_booking.id,
            time=datetime.now(),
            hobbs_start=100.0,
            tach_start=200.0,
            fuel_level='full'
        )
        _db.session.add(check_in)
        _db.session.commit()
        return check_in

@pytest.fixture
def test_check_out(_db, test_booking):
    """Create a test check-out."""
    with _db.session.begin():
        check_out = CheckOut(
            booking_id=test_booking.id,
            time=datetime.now() + timedelta(hours=2),
            hobbs_end=102.0,
            tach_end=202.0,
            fuel_level='tabs'
        )
        _db.session.add(check_out)
        _db.session.commit()
        return check_out

@pytest.fixture
def test_invoice(_db, test_booking):
    """Create a test invoice."""
    with _db.session.begin():
        invoice = Invoice(
            booking_id=test_booking.id,
            amount=240.00,
            status='pending'
        )
        _db.session.add(invoice)
        _db.session.commit()
        return invoice

@pytest.fixture
def auth(client):
    """Authentication helper class."""
    class AuthActions:
        def __init__(self, client):
            self._client = client

        def login(self, email='test@example.com', password='password123'):
            return self._client.post('/auth/login', data={
                'email': email,
                'password': password
            }, follow_redirects=True)

        def logout(self):
            return self._client.get('/auth/logout', follow_redirects=True)

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
    return client

@pytest.fixture
def logged_in_admin(client, test_admin, app):
    """Log in a test admin user."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
            sess['csrf_token'] = 'test-token'
        login_user(test_admin)
    return client

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
