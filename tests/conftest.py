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

@pytest.fixture(scope='function')
def app():
    """Create and configure a new app instance for each test."""
    app = create_app('testing')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    # Initialize the app context
    ctx = app.app_context()
    ctx.push()
    
    yield app
    
    ctx.pop()

@pytest.fixture(scope='function')
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture(scope='function')
def _db(app):
    """Create a new database for each test."""
    db.create_all()
    yield db
    db.session.remove()
    db.drop_all()

@pytest.fixture(scope='function')
def session(app, _db):
    """Create a new database session for each test."""
    connection = _db.engine.connect()
    transaction = connection.begin()
    
    # Create a session factory bound to this connection
    session_factory = sessionmaker(bind=connection)
    
    # Create a scoped session to ensure thread-local session management
    session = scoped_session(session_factory)
    
    # Make the session the current one for SQLAlchemy
    _db.session = session
    
    yield session
    
    # Cleanup
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
        email='test_user@example.com',
        first_name='Test',
        last_name='User',
        phone='123-456-7890',
        student_id='STU001',
        status='active',
        role='student'
    )
    user.set_password('password123')
    session.add(user)
    session.commit()
    return user

@pytest.fixture(scope='function')
def test_instructor(session):
    """Create a test instructor."""
    instructor = User(
        email='test_instructor@example.com',
        first_name='Test',
        last_name='Instructor',
        phone='123-456-7890',
        status='active',
        role='instructor'
    )
    instructor.set_password('password123')
    session.add(instructor)
    session.commit()
    return instructor

@pytest.fixture(scope='function')
def test_admin(session):
    """Create a test admin user."""
    admin = User(
        email='test_admin@example.com',
        first_name='Test',
        last_name='Admin',
        phone='123-456-7890',
        status='active',
        role='admin'
    )
    admin.set_password('password123')
    session.add(admin)
    session.commit()
    return admin

@pytest.fixture(scope='function')
def test_aircraft(session):
    """Create a test aircraft."""
    aircraft = Aircraft(
        registration='N1234',
        make_model='Piper Cherokee',
        year=2019,
        status='active',
        rate_per_hour=150.0
    )
    session.add(aircraft)
    session.commit()
    return aircraft

@pytest.fixture(scope='function')
def auth_client(app, client, test_user, session):
    """A test client with a logged-in user."""
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
            sess['_fresh'] = True
        login_user(test_user)
        session.add(test_user)
        session.commit()
    return client

@pytest.fixture(scope='function')
def admin_client(app, client, test_admin, session):
    """A test client with a logged-in admin user."""
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_admin.id)
            sess['_fresh'] = True
        login_user(test_admin)
        session.add(test_admin)
        session.commit()
    return client

@pytest.fixture(scope='function')
def test_booking(session, test_user, test_aircraft):
    """Create a test booking."""
    booking = Booking(
        student_id=test_user.id,
        aircraft_id=test_aircraft.id,
        start_time=datetime.now(UTC) + timedelta(days=1),
        end_time=datetime.now(UTC) + timedelta(days=1, hours=1),
        status='confirmed'
    )
    session.add(booking)
    session.commit()
    return booking

@pytest.fixture(scope='function')
def test_check_in(session, test_booking):
    """Create a test check-in."""
    check_in = CheckIn(
        booking_id=test_booking.id,
        hobbs_start=1234.5,
        tach_start=2345.6,
        notes='Pre-flight inspection completed'
    )
    session.add(check_in)
    session.commit()
    return check_in

@pytest.fixture(scope='function')
def test_check_out(session, test_check_in):
    """Create a test check-out."""
    check_out = CheckOut(
        check_in_id=test_check_in.id,
        hobbs_end=1235.5,
        tach_end=2346.6,
        notes='Post-flight inspection completed'
    )
    session.add(check_out)
    session.commit()
    return check_out

@pytest.fixture(scope='function')
def test_invoice(session, test_booking):
    """Create a test invoice."""
    invoice = Invoice(
        booking_id=test_booking.id,
        amount=150.0,
        status='pending'
    )
    session.add(invoice)
    session.commit()
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
            sess['user_id'] = test_user.id
            sess['_fresh'] = True
    return client

@pytest.fixture
def logged_in_admin(app, client, test_admin):
    """A test client with a logged-in admin user."""
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    return client

@pytest.fixture
def logged_in_instructor(app, client, test_instructor):
    """A test client with a logged-in instructor."""
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_instructor.id
            sess['_fresh'] = True
    return client
