import pytest
from app import create_app, db
from app.models import User, Aircraft, Booking
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
            db.session.commit()
            # Create a student user
            student = User(email="student@example.com", first_name="Student", last_name="User", role="student", status="active")
            student.set_password("password")
            db.session.add(student)
            # Create an instructor
            instructor = User(email="instructor@example.com", first_name="Inst", last_name="Ructor", role="instructor", status="active")
            instructor.set_password("password")
            db.session.add(instructor)
            # Create an available aircraft
            ac = Aircraft(registration="N77777", make="Test", model="Model", year=2022, category="single_engine_land", rate_per_hour=99, status="available")
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

def test_booking_create(client):
    client, app = client
    login_student(client, app)
    with app.app_context():
        ac = Aircraft.query.filter_by(registration="N77777").first()
    start_time = datetime.now(timezone.utc).replace(microsecond=0, second=0)
    resp = client.post("/bookings", data={
        "aircraft_id": ac.id,
        "start_time": start_time.strftime("%Y-%m-%dT%H:%M"),
        "duration": 60
    }, follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        booking = Booking.query.filter_by(aircraft_id=ac.id).first()
        assert booking is not None
        assert booking.start_time is not None
        assert booking.end_time == booking.start_time + timedelta(minutes=60)

def test_booking_cancel(client):
    client, app = client
    login_student(client, app)
    with app.app_context():
        ac = Aircraft.query.filter_by(registration="N77777").first()
    start_time = datetime.now(timezone.utc).replace(microsecond=0, second=0)
    resp = client.post("/bookings", data={
        "aircraft_id": ac.id,
        "start_time": start_time.strftime("%Y-%m-%dT%H:%M"),
        "duration": 60
    }, follow_redirects=True)
    with app.app_context():
        booking = Booking.query.filter_by(aircraft_id=ac.id).first()
        assert booking is not None
    resp = client.post(f"/bookings/{booking.id}/cancel", follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        booking = Booking.query.get(booking.id)
        assert booking.status == "cancelled" or booking.status == "canceled"
