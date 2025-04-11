import os
import tempfile
import pytest
from datetime import datetime, timedelta, UTC
from app import create_app, db
from app.models import User, Aircraft, Booking, MaintenanceType, MaintenanceRecord, Squawk, CheckIn, CheckOut, Invoice
from flask import session as flask_session
from flask_login import login_user
from sqlalchemy.orm import scoped_session, sessionmaker
import sqlalchemy as sa
from flask import Flask
from sqlalchemy import event
from flask_sqlalchemy import SQLAlchemy

@pytest.fixture(scope='function')
def app():
    """Create and configure a new app instance for each test."""
    app = create_app('testing')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='function')
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture(scope='function')
def session(app):
    """Create a new database session for each test."""
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        
        session_factory = sessionmaker(bind=connection)
        session = scoped_session(session_factory)
        
        db.session = session
        
        yield session
        
        session.remove()
        transaction.rollback()
        connection.close()

@pytest.fixture(scope='function')
def runner(app):
    """Create a test CLI runner."""
    return app.test_cli_runner()

@pytest.fixture(scope='function')
def test_user(session):
    """Create a test user."""
    user = User(
        email='test@example.com',
        first_name='Test',
        last_name='User',
        role='student'
    )
    user.set_password('password123')
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@pytest.fixture(scope='function')
def test_instructor(session):
    """Create a test instructor."""
    instructor = User(
        email='instructor@example.com',
        first_name='Test',
        last_name='Instructor',
        role='instructor',
        is_instructor=True
    )
    instructor.set_password('password123')
    session.add(instructor)
    session.commit()
    session.refresh(instructor)
    return instructor

@pytest.fixture(scope='function')
def test_admin(session):
    """Create a test admin."""
    admin = User(
        email='admin@example.com',
        first_name='Test',
        last_name='Admin',
        role='admin',
        is_admin=True
    )
    admin.set_password('password123')
    session.add(admin)
    session.commit()
    session.refresh(admin)
    return admin

@pytest.fixture(scope='function')
def test_aircraft(session):
    """Create a test aircraft."""
    aircraft = Aircraft(
        registration='N12345',
        make_model='Cessna 172',
        year=2020,
        status='available',
        rate_per_hour=150.0
    )
    session.add(aircraft)
    session.commit()
    session.refresh(aircraft)
    return aircraft

@pytest.fixture(scope='function')
def auth_client(client, test_user):
    """Create a test client with a logged-in user."""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_user.id
        sess['_fresh'] = True
    return client

@pytest.fixture(scope='function')
def admin_client(client, test_admin):
    """Create a test client with a logged-in admin."""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_admin.id
        sess['_fresh'] = True
    return client

@pytest.fixture(scope='function')
def test_booking(session, test_user, test_instructor, test_aircraft):
    """Create a test booking."""
    booking = Booking(
        student_id=test_user.id,
        instructor_id=test_instructor.id,
        aircraft_id=test_aircraft.id,
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(hours=1),
        status='confirmed'
    )
    session.add(booking)
    session.commit()
    session.refresh(booking)
    return booking

@pytest.fixture(scope='function')
def test_check_in(session, test_booking):
    """Create a test check-in."""
    check_in = CheckIn(
        booking_id=test_booking.id,
        aircraft_id=test_booking.aircraft_id,
        instructor_id=test_booking.instructor_id,
        hobbs_start=1234.5,
        tach_start=2345.6,
        notes='Pre-flight inspection completed'
    )
    session.add(check_in)
    session.commit()
    session.refresh(check_in)
    return check_in

@pytest.fixture(scope='function')
def test_check_out(session, test_check_in):
    """Create a test check-out."""
    check_out = CheckOut(
        booking_id=test_check_in.booking_id,
        aircraft_id=test_check_in.aircraft_id,
        instructor_id=test_check_in.instructor_id,
        hobbs_end=1235.5,
        tach_end=2346.6,
        total_aircraft_time=1.0,
        notes='Post-flight inspection completed'
    )
    session.add(check_out)
    session.commit()
    session.refresh(check_out)
    return check_out

@pytest.fixture(scope='function')
def test_invoice(session, test_booking):
    """Create a test invoice."""
    invoice = Invoice(
        booking_id=test_booking.id,
        amount=100.00,
        status='pending'
    )
    session.add(invoice)
    session.commit()
    session.refresh(invoice)
    return invoice

@pytest.fixture
def auth(client):
    """Authentication actions for tests."""
    class AuthActions:
        def __init__(self, client):
            self._client = client

        def login(self, email='test@example.com', password='password123'):
            return self._client.post('/auth/login', data={
                'email': email,
                'password': password
            })

        def logout(self):
            return self._client.get('/auth/logout')

    return AuthActions(client)

@pytest.fixture
def logged_in_user(app, client, test_user):
    """A test client with a logged-in regular user."""
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_user.id
            sess['_fresh'] = True
    return client

@pytest.fixture
def logged_in_admin(app, client, test_admin):
    """A test client with a logged-in admin user."""
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_admin.id
            sess['_fresh'] = True
    return client

@pytest.fixture
def logged_in_instructor(app, client, test_instructor):
    """A test client with a logged-in instructor."""
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_instructor.id
            sess['_fresh'] = True
    return client
