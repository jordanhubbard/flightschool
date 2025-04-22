import pytest
from app import create_app, db
from app.models import Aircraft
from datetime import date

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            ac = Aircraft(
                registration="N12345",
                make="Cessna",
                model="172S",
                year=2020,
                status="available",
                rate_per_hour=120,
                time_to_next_oil_change=12.5,
                time_to_next_100hr=88.0,
                date_of_next_annual=date(2025, 12, 15)
            )
            db.session.add(ac)
            db.session.commit()
        yield client, app
        with app.app_context():
            db.drop_all()

def test_aircraft_info_route(client):
    client, app = client
    with app.app_context():
        ac = Aircraft.query.filter_by(registration="N12345").first()
        assert ac is not None
        url = f"/aircraft/{ac.id}/info"
    resp = client.get(url)
    assert resp.status_code == 200
    assert b"Cessna 172S" in resp.data
    assert b"12.5 hours" in resp.data
    assert b"88.0 hours" in resp.data
    assert b"2025-12-15" in resp.data

def test_aircraft_info_404(client):
    client, app = client
    resp = client.get("/aircraft/99999/info")
    assert resp.status_code == 404
