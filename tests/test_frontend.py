import pytest
from flask import url_for
from bs4 import BeautifulSoup
from app import create_app, db
from app.models import User

@pytest.fixture
def client():
    app = create_app()
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # Create a student user for login
            user = User(email='student@example.com', first_name='Jane', last_name='Doe', role='student', status='active')
            user.set_password('student123')
            db.session.add(user)
            db.session.commit()
        yield client
        with app.app_context():
            db.drop_all()

def login(client, email, password):
    return client.post('/login', data={
        'email': email,
        'password': password
    }, follow_redirects=True)

def test_booking_page_renders_calendar_and_time(client):
    login(client, 'student@example.com', 'student123')
    response = client.get('/bookings')
    assert response.status_code == 200
    soup = BeautifulSoup(response.data, 'html.parser')
    # Check for current time label
    label = soup.find('label', {'class': 'form-label'})
    assert label and 'Current Time:' in label.text
    # Check for calendar-widget div
    cal_div = soup.find('div', {'id': 'calendar-widget'})
    assert cal_div is not None

def test_booking_page_includes_booking_blocks_js(client):
    login(client, 'student@example.com', 'student123')
    response = client.get('/bookings')
    assert response.status_code == 200
    # Check that booking_blocks JSON is present in the page
    assert b'const BOOKING_BLOCKS' in response.data
    assert b'calendar-widget' in response.data
