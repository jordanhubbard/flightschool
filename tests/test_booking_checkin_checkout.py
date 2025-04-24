import pytest
from app import create_app, db
from app.models import User, Aircraft, Booking, CheckIn, CheckOut
from datetime import datetime, timedelta, timezone

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            db.session.query(User).delete()
            db.session.query(Aircraft).delete()
            db.session.query(Booking).delete()
            db.session.commit()
            # Create users
            student = User(email="student@example.com", first_name="Student", last_name="User", role="student", status="active")
            student.set_password("password")
            db.session.add(student)
            instructor = User(email="instructor@example.com", first_name="Inst", last_name="Ructor", role="instructor", status="active")
            instructor.set_password("password")
            db.session.add(instructor)
            # Create aircraft
            ac = Aircraft(registration="N55555", make="Test", model="Model", year=2022, category="single_engine_land", rate_per_hour=99, status="available",
                time_to_next_oil_change=40.0,
                time_to_next_100hr=80.0,
                date_of_next_annual=None
            )
            db.session.add(ac)
            db.session.commit()
        yield client, app
        with app.app_context():
            db.drop_all()

def login_student(client, app):
    with app.app_context():
        student = User.query.filter_by(email="student@example.com").first()
    with client.session_transaction() as sess:
        sess["_user_id"] = str(student.id)
        sess["_fresh"] = True

def test_booking_checkin_checkout(client):
    client, app = client
    login_student(client, app)
    
    with app.app_context():
        ac = Aircraft.query.filter_by(registration="N55555").first()
        assert ac.time_to_next_oil_change == 40.0
        assert ac.time_to_next_100hr == 80.0
        assert ac.date_of_next_annual is None
        
        # Create a booking
        booking = Booking(
            student_id=User.query.filter_by(email="student@example.com").first().id,
            aircraft_id=ac.id,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(hours=2),
            status="confirmed"
        )
        db.session.add(booking)
        db.session.commit()
        booking_id = booking.id  # Store the ID to use outside the context
        aircraft_id = ac.id  # Store the ID to use outside the context
    
    # Check in
    response = client.post(f"/flight/check-in/{booking_id}", data={
        "hobbs_start": 100.0,
        "tach_start": 90.0,
        "weather_conditions_acceptable": "on"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Flight Status" in response.data
    
    with app.app_context():
        # Verify check-in record
        booking = Booking.query.get(booking_id)
        assert booking.status == "in_progress"
        assert booking.check_in is not None
        assert booking.check_in.hobbs_start == 100.0
        assert booking.check_in.tach_start == 90.0
    
    # Check out
    response = client.post(f"/flight/check-out/{booking_id}", data={
        "hobbs_end": 102.0,
        "tach_end": 91.5
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Flight Summary" in response.data
    
    with app.app_context():
        # Verify check-out record
        booking = Booking.query.get(booking_id)
        assert booking.status == "completed"
        assert booking.check_out is not None
        assert booking.check_out.hobbs_end == 102.0
        assert booking.check_out.tach_end == 91.5
        
        # Verify aircraft times were updated
        ac = Aircraft.query.get(aircraft_id)
        assert ac.hobbs_time == 102.0
        assert ac.tach_time == 91.5
        
        # Verify maintenance times were updated
        expected_oil_change_time = 40.0 - (102.0 - 100.0)
        expected_100hr_time = 80.0 - (102.0 - 100.0)
        assert ac.time_to_next_oil_change == expected_oil_change_time
        assert ac.time_to_next_100hr == expected_100hr_time

def test_checkin_invalid_booking(client):
    client, app = client
    login_student(client, app)
    resp = client.get("/flight/check-in/999999")
    assert resp.status_code == 404

def test_checkin_twice(client):
    client, app = client
    login_student(client, app)
    with app.app_context():
        ac = Aircraft.query.filter_by(registration="N55555").first()
        
        # Create a booking
        booking = Booking(
            student_id=User.query.filter_by(email="student@example.com").first().id,
            aircraft_id=ac.id,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(hours=2),
            status="confirmed"
        )
        db.session.add(booking)
        db.session.commit()
        booking_id = booking.id
    
    # First check-in
    resp = client.post(f"/flight/check-in/{booking_id}", data={
        "hobbs_start": 100.0,
        "tach_start": 90.0,
        "weather_conditions_acceptable": "on"
    }, follow_redirects=True)
    assert resp.status_code == 200
    
    # Try to check in again
    resp = client.get(f"/flight/check-in/{booking_id}", follow_redirects=True)
    assert resp.status_code == 200
    assert b"This flight has already been checked in" in resp.data

def test_checkout_without_checkin(client):
    client, app = client
    login_student(client, app)
    with app.app_context():
        ac = Aircraft.query.filter_by(registration="N55555").first()
        
        # Create a booking
        booking = Booking(
            student_id=User.query.filter_by(email="student@example.com").first().id,
            aircraft_id=ac.id,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(hours=2),
            status="confirmed"
        )
        db.session.add(booking)
        db.session.commit()
        booking_id = booking.id
    
    # Try to check out without checking in
    resp = client.get(f"/flight/check-out/{booking_id}", follow_redirects=True)
    assert resp.status_code == 200
    assert b"You must check in before checking out" in resp.data

def test_checkout_twice(client):
    client, app = client
    login_student(client, app)
    with app.app_context():
        ac = Aircraft.query.filter_by(registration="N55555").first()
        
        # Create a booking
        booking = Booking(
            student_id=User.query.filter_by(email="student@example.com").first().id,
            aircraft_id=ac.id,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(hours=2),
            status="confirmed"
        )
        db.session.add(booking)
        db.session.commit()
        booking_id = booking.id
        
        # Create check-in record
        check_in = CheckIn(
            booking_id=booking_id,
            aircraft_id=ac.id,
            check_in_time=datetime.now(timezone.utc),
            hobbs_start=100.0,
            tach_start=90.0,
            weather_conditions_acceptable=True
        )
        db.session.add(check_in)
        booking.status = "in_progress"
        db.session.commit()
    
    # First check-out
    resp = client.post(f"/flight/check-out/{booking_id}", data={
        "hobbs_end": 102.0,
        "tach_end": 91.5
    }, follow_redirects=True)
    assert resp.status_code == 200
    
    # Try to check out again
    resp = client.get(f"/flight/check-out/{booking_id}", follow_redirects=True)
    assert resp.status_code == 200
    assert b"This flight has already been checked out" in resp.data

def test_checkin_missing_fields(client):
    client, app = client
    login_student(client, app)
    with app.app_context():
        ac = Aircraft.query.filter_by(registration="N55555").first()
        
        # Create a booking
        booking = Booking(
            student_id=User.query.filter_by(email="student@example.com").first().id,
            aircraft_id=ac.id,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(hours=2),
            status="confirmed"
        )
        db.session.add(booking)
        db.session.commit()
        booking_id = booking.id
    
    # Check in with missing fields
    resp = client.post(f"/flight/check-in/{booking_id}", data={
        # Missing hobbs_start
        "tach_start": 90.0
    })
    assert resp.status_code == 400
