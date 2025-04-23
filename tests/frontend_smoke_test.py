import pytest
import requests

# Set this to the correct port if your app runs on a different one
BASE_URL = "http://127.0.0.1:5000"

# List of endpoints to smoke test
ENDPOINTS = [
    "/",
    "/login",
    "/logout",
    "/bookings",
    "/bookings/dashboard",
    "/bookings/recurring",
    "/bookings/waitlist",
    "/admin",
    "/admin/dashboard",
    "/admin/schedule",
    "/settings/calendar",
    "/settings/calendar/authorize",
    "/settings/calendar/disconnect",
    "/settings/calendar/callback",
    "/aircraft",
    "/bookings/list",
    "/bookings/weather-minima",
]

@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_endpoint_up(endpoint):
    url = BASE_URL + endpoint
    resp = requests.get(url, allow_redirects=True)
    # Accept 2xx or 3xx as success
    assert resp.status_code < 400, f"{endpoint} returned status {resp.status_code}"
    # Should not include a Python traceback or Flask error page
    assert b"Traceback" not in resp.content
    assert b"Internal Server Error" not in resp.content
