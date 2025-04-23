import pytest
from app import create_app, db
from app.models import User, Aircraft
from flask_login import login_user

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # Remove existing users to avoid unique constraint error
            db.session.query(User).delete()
            db.session.commit()
            # Create admin user
            admin = User(email="admin@example.com", first_name="Admin", last_name="User", role="admin", is_admin=True, status="active")
            admin.set_password("password")
            db.session.add(admin)
            db.session.commit()
        yield client, app
        with app.app_context():
            db.drop_all()

def login_admin(client, app):
    with app.app_context():
        admin = User.query.filter_by(email="admin@example.com").first()
    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin.id)
        sess["_fresh"] = True

def test_admin_dashboard_access(client):
    client, app = client
    login_admin(client, app)
    resp = client.get("/admin/dashboard")
    assert resp.status_code == 200
    assert b"Admin Dashboard" in resp.data

def test_admin_aircraft_add(client):
    client, app = client
    login_admin(client, app)
    resp = client.post("/admin/aircraft/create", data={
        "registration": "N99999",
        "make": "TestMake",
        "model": "TestModel",
        "year": 2024,
        "category": "single_engine_land",
        "rate_per_hour": 100,
        "status": "available"
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Aircraft added successfully" in resp.data
    ac = Aircraft.query.filter_by(registration="N99999").first()
    assert ac is not None
    assert ac.make == "TestMake"

def test_admin_aircraft_maintenance_fields(client):
    client, app = client
    login_admin(client, app)
    resp = client.post("/admin/aircraft/create", data={
        "registration": "N77777",
        "make": "Test",
        "model": "Model",
        "year": 2023,
        "status": "available",
        "rate_per_hour": 100,
        "time_to_next_oil_change": 25.5,
        "time_to_next_100hr": 50.0,
        "date_of_next_annual": "2025-11-30"
    }, follow_redirects=True)
    assert b"Aircraft added successfully" in resp.data
    ac = Aircraft.query.filter_by(registration="N77777").first()
    assert ac is not None
    assert ac.time_to_next_oil_change == 25.5
    assert ac.time_to_next_100hr == 50.0
    assert ac.date_of_next_annual.strftime('%Y-%m-%d') == "2025-11-30"

def test_admin_aircraft_delete(client):
    client, app = client
    login_admin(client, app)
    # Add then delete
    client.post("/admin/aircraft/create", data={
        "registration": "N88888",
        "make": "DelMake",
        "model": "DelModel",
        "year": 2023,
        "category": "single_engine_land",
        "rate_per_hour": 120,
        "status": "available"
    }, follow_redirects=True)
    ac = Aircraft.query.filter_by(registration="N88888").first()
    assert ac is not None
    resp = client.delete(f"/admin/aircraft/{ac.id}/delete")
    assert resp.status_code == 200
    assert b"deleted successfully" in resp.data
