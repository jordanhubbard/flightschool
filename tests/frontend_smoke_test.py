import pytest
import requests

# Set this to the correct port if your app runs on a different one
BASE_URL = "http://127.0.0.1:5001"

# Endpoints with no required path parameters
ENDPOINTS = [
    "/",
    "/about",
    "/contact",
    "/profile",
    "/training",
    "/aircraft",
    "/instructors",
    "/faq",
    "/debug",
    "/auth/login",
    "/auth/logout",
    "/auth/account-settings",
    "/auth/google-auth",
    "/auth/google-callback",
    "/auth/register",
    "/auth/documents",
    "/auth/flight-logs",
    "/google-auth",
    "/google-callback",
    "/dashboard",
    "/instructor/dashboard",
    "/bookings",
    "/bookings/weather-minima",
    "/bookings",
    "/settings/calendar",
    "/settings/calendar/authorize",
    "/settings/calendar/callback",
    "/settings/calendar/disconnect",
    "/recurring-bookings",
    "/waitlist",
    "/admin/dashboard",
    "/admin/calendar/oauth",
    "/admin/calendar/callback",
    "/admin/schedule",
    "/admin/reports",
    "/admin/settings",
    "/admin/user/create",
    "/admin/aircraft/create",
    "/admin/maintenance/types",
    "/admin/maintenance/records",
    "/admin/squawks",
    "/admin/aircraft",
    "/admin/aircraft/add",
    "/admin/instructors",
    "/admin/users",
    "/admin/instructor/create",
    "/admin/endorsements",
    "/admin/documents",
    "/admin/weather-minima",
    "/admin/audit-logs",
    "/admin/waitlist",
    "/admin/recurring-bookings",
    "/admin/flight-logs",
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
