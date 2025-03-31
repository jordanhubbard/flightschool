import pytest
from datetime import datetime, timedelta, UTC
from app import create_app, db
from app.models import User, Aircraft, Booking, CheckIn, CheckOut, Invoice

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def test_user(app):
    user = User(
        email='test@example.com',
        first_name='Test',
        last_name='User',
        is_admin=False
    )
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def test_admin(app):
    admin = User(
        email='admin@example.com',
        first_name='Admin',
        last_name='User',
        is_admin=True
    )
    admin.set_password('admin123')
    db.session.add(admin)
    db.session.commit()
    return admin

@pytest.fixture
def test_aircraft(app):
    aircraft = Aircraft(
        tail_number='N12345',
        make_model='Cessna 172',
        year=2020,
        status='available',
        rate_per_hour=150.00
    )
    db.session.add(aircraft)
    db.session.commit()
    return aircraft

@pytest.fixture
def test_instructor(app):
    instructor = User(
        email='instructor@example.com',
        first_name='John',
        last_name='Doe',
        phone='123-456-7890',
        certificates='CFI, CFII',
        is_admin=False,
        is_instructor=True,
        status='active',
        instructor_rate_per_hour=75.00
    )
    instructor.set_password('instructor123')
    db.session.add(instructor)
    db.session.commit()
    return instructor

@pytest.fixture
def test_booking(app, test_user, test_aircraft, test_instructor):
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
    return booking

@pytest.fixture
def test_check_in(app, test_booking):
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
    return check_in

@pytest.fixture
def test_check_out(app, test_booking, test_check_in):
    check_out = CheckOut(
        booking_id=test_booking.id,
        aircraft_id=test_booking.aircraft_id,
        instructor_id=test_booking.instructor_id,
        hobbs_end=1236.2,
        tach_end=2347.1,
        instructor_end_time=datetime.now(UTC),
        total_aircraft_time=1.7,
        total_instructor_time=2.0,
        notes='Touch and go practice completed'
    )
    db.session.add(check_out)
    db.session.commit()
    return check_out

@pytest.fixture
def test_invoice(app, test_booking, test_check_out):
    invoice = Invoice(
        booking_id=test_booking.id,
        aircraft_id=test_booking.aircraft_id,
        student_id=test_booking.student_id,
        instructor_id=test_booking.instructor_id,
        invoice_number='INV-2024-001',
        aircraft_rate=test_booking.aircraft.rate_per_hour,
        instructor_rate=test_booking.instructor.instructor_rate_per_hour,
        aircraft_time=test_check_out.total_aircraft_time,
        instructor_time=test_check_out.total_instructor_time,
        aircraft_total=test_check_out.total_aircraft_time * test_booking.aircraft.rate_per_hour,
        instructor_total=test_check_out.total_instructor_time * test_booking.instructor.instructor_rate_per_hour,
        total_amount=(test_check_out.total_aircraft_time * test_booking.aircraft.rate_per_hour) + 
                    (test_check_out.total_instructor_time * test_booking.instructor.instructor_rate_per_hour),
        status='pending',
        notes='Initial training flight'
    )
    db.session.add(invoice)
    db.session.commit()
    return invoice

@pytest.fixture
def with_csrf_token(client):
    with client.session_transaction() as session:
        session['csrf_token'] = 'test_token'
    return client 