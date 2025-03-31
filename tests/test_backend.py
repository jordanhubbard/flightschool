from flask_login import current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from flask import session
from app.models import User, Aircraft, Booking
from app import db
import pytest

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    name = db.Column(db.String(128))  # Full name, computed from first_name and last_name
    phone = db.Column(db.String(20))
    address = db.Column(db.String(256))
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    is_instructor = db.Column(db.Boolean, default=False)
    student_id = db.Column(db.String(20), unique=True)
    certificates = db.Column(db.String(200))
    status = db.Column(db.String(20), default='active')  # active, unavailable, inactive
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Google Calendar Integration
    google_calendar_enabled = db.Column(db.Boolean, default=False)
    google_calendar_token = db.Column(db.String(500))
    google_calendar_refresh_token = db.Column(db.String(500))
    google_calendar_token_expiry = db.Column(db.DateTime)
    google_calendar_id = db.Column(db.String(100))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.name
    
    def __repr__(self):
        return f'<User {self.email}>'

def test_instructor_management(client, test_admin, app):
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.post('/admin/instructor/create', data={
        'email': 'new.instructor@example.com',
        'first_name': 'New',
        'last_name': 'Instructor',
        'phone': '123-456-7890',
        'certificates': 'CFI',
        'status': 'active'
    }, follow_redirects=True)
    assert b'Instructor created successfully' in response.data

def test_google_calendar_settings(client, test_admin, app):
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.get('/admin/calendar/settings')
    assert response.status_code == 200
    assert b'Calendar Settings' in response.data

def test_google_calendar_oauth(client, test_admin, app):
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.get('/admin/calendar/oauth')
    assert response.status_code == 302
    assert 'accounts.google.com' in response.location

def test_booking_management(client, test_user, test_aircraft, app):
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.id
            sess['_fresh'] = True
        
        # Create a booking
        booking = Booking(
            student_id=test_user.id,
            aircraft_id=test_aircraft.id,
            instructor_id=None,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            status='pending'
        )
        db.session.add(booking)
        db.session.commit()
        db.session.refresh(booking)
    
    # Test viewing the booking
    response = client.get(f'/booking/{booking.id}')
    assert response.status_code == 200
    assert test_aircraft.registration.encode() in response.data
    assert b'Pending' in response.data

def test_booking_cancellation(client, test_user, test_aircraft, app):
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.id
            sess['_fresh'] = True
        
        # Create a booking
        booking = Booking(
            student_id=test_user.id,
            aircraft_id=test_aircraft.id,
            instructor_id=None,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            status='pending'
        )
        db.session.add(booking)
        db.session.commit()
        db.session.refresh(booking)
    
    # Test canceling the booking
    response = client.post(f'/booking/{booking.id}/cancel')
    assert response.status_code == 200
    assert b'Booking cancelled successfully' in response.data

def test_user_management(client, test_admin, app):
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.post('/admin/user/create', data={
        'email': 'new.student@example.com',
        'first_name': 'New',
        'last_name': 'Student',
        'phone': '123-456-7890',
        'student_id': 'STU001',
        'status': 'active',
        'role': 'student'
    }, follow_redirects=True)
    assert b'User created successfully' in response.data

def test_aircraft_management(client, test_admin, app):
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.post('/admin/aircraft/create', data={
        'registration': 'N54321',
        'make_model': 'Piper Cherokee',
        'year': '2019',
        'status': 'active'
    }, follow_redirects=True)
    assert b'Aircraft created successfully' in response.data

def test_schedule_management(client, test_admin, app):
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.get('/admin/schedule')
    assert response.status_code == 200
    assert b'Schedule Management' in response.data

def test_report_generation(client, test_admin, app):
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.get('/admin/reports')
    assert response.status_code == 200
    assert b'Report Generation' in response.data

def test_system_settings(client, test_admin, app):
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['_fresh'] = True
    
    response = client.get('/admin/settings')
    assert response.status_code == 200
    assert b'System Settings' in response.data 