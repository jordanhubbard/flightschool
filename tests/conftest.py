import os
import tempfile
import pytest
from app import create_app, db
from app.models import User, Aircraft, Booking, MaintenanceType, MaintenanceRecord, Squawk
from datetime import datetime
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
        from app.models import User, Aircraft, Booking, MaintenanceType, MaintenanceRecord, Squawk
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
            first_name='Test',
            last_name='Instructor',
            role='instructor',
            is_admin=False,
            is_instructor=True,
            status='active'
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
            year=2015,
            status='available'
        )
        db.session.add(aircraft)
        db.session.commit()
        db.session.refresh(aircraft)  # Refresh the instance to ensure it's bound to the session
        yield aircraft
        db.session.rollback()

@pytest.fixture
def auth(client):
    """Authentication helper class."""
    class AuthActions:
        def __init__(self, client):
            self._client = client

        def login(self, email='test@example.com', password='password123'):  # Updated password to match fixture
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