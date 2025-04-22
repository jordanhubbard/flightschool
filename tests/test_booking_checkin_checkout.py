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
            ac = Aircraft(registration="N55555", make="Test", model="Model", year=2022, category="single_engine_land", rate_per_hour=99, status="available")
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
    # Create booking with start_time and duration
    start = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0, second=0)
    resp = client.post("/bookings", data={
        "aircraft_id": ac.id,
        "start_time": start.strftime("%Y-%m-%dT%H:%M"),
        "duration": 60
    }, follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        booking = Booking.query.filter_by(aircraft_id=ac.id).first()
        assert booking is not None
    # Simulate check-in
    resp = client.post(f"/check-in/{booking.id}", data={
        "hobbs_start": 100.0,
        "tach_start": 200.0
    }, follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        checkin = CheckIn.query.filter_by(booking_id=booking.id).first()
        assert checkin is not None
        assert checkin.hobbs_start == 100.0
    # Simulate check-out
    resp = client.post(f"/check-out/{booking.id}", data={
        "hobbs_end": 101.0,
        "tach_end": 201.0,
        "notes": "All good."
    }, follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        checkout = CheckOut.query.filter_by(booking_id=booking.id).first()
        assert checkout is not None
        assert checkout.hobbs_end == 101.0

def test_checkin_invalid_booking(client):
    client, app = client
    login_student(client, app)
    resp = client.post("/check-in/9999", data={"hobbs_start": 100, "tach_start": 200}, follow_redirects=True)
    assert resp.status_code == 404

def test_checkin_twice(client):
    client, app = client
    login_student(client, app)
    with app.app_context():
        ac = Aircraft.query.filter_by(registration="N55555").first()
    start = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0, second=0)
    client.post("/bookings", data={"aircraft_id": ac.id, "start_time": start.strftime("%Y-%m-%dT%H:%M"), "duration": 60}, follow_redirects=True)
    with app.app_context():
        booking = Booking.query.filter_by(aircraft_id=ac.id).first()
    client.post(f"/check-in/{booking.id}", data={"hobbs_start": 100, "tach_start": 200}, follow_redirects=True)
    resp = client.post(f"/check-in/{booking.id}", data={"hobbs_start": 101, "tach_start": 201}, follow_redirects=True)
    assert resp.status_code == 400
    assert b"Already checked in" in resp.data

def test_checkout_without_checkin(client):
    client, app = client
    login_student(client, app)
    with app.app_context():
        ac = Aircraft.query.filter_by(registration="N55555").first()
    start = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0, second=0)
    client.post("/bookings", data={"aircraft_id": ac.id, "start_time": start.strftime("%Y-%m-%dT%H:%M"), "duration": 60}, follow_redirects=True)
    with app.app_context():
        booking = Booking.query.filter_by(aircraft_id=ac.id).first()
    resp = client.post(f"/check-out/{booking.id}", data={"hobbs_end": 101, "tach_end": 201}, follow_redirects=True)
    assert resp.status_code == 400
    assert b"Must check in before checking out" in resp.data

def test_checkout_twice(client):
    client, app = client
    login_student(client, app)
    with app.app_context():
        ac = Aircraft.query.filter_by(registration="N55555").first()
    start = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0, second=0)
    client.post("/bookings", data={"aircraft_id": ac.id, "start_time": start.strftime("%Y-%m-%dT%H:%M"), "duration": 60}, follow_redirects=True)
    with app.app_context():
        booking = Booking.query.filter_by(aircraft_id=ac.id).first()
    client.post(f"/check-in/{booking.id}", data={"hobbs_start": 100, "tach_start": 200}, follow_redirects=True)
    client.post(f"/check-out/{booking.id}", data={"hobbs_end": 101, "tach_end": 201}, follow_redirects=True)
    resp = client.post(f"/check-out/{booking.id}", data={"hobbs_end": 102, "tach_end": 202}, follow_redirects=True)
    assert resp.status_code == 400
    assert b"Already checked out" in resp.data

def test_checkin_missing_fields(client):
    client, app = client
    login_student(client, app)
    with app.app_context():
        ac = Aircraft.query.filter_by(registration="N55555").first()
    start = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0, second=0)
    client.post("/bookings", data={"aircraft_id": ac.id, "start_time": start.strftime("%Y-%m-%dT%H:%M"), "duration": 60}, follow_redirects=True)
    with app.app_context():
        booking = Booking.query.filter_by(aircraft_id=ac.id).first()
    resp = client.post(f"/check-in/{booking.id}", data={"hobbs_start": ""}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"This field is required" in resp.data or b"error" in resp.data or b"Invalid" in resp.data
