import os
import pytest
from app.models import ensure_aircraft_image


def test_ensure_aircraft_image_default():
    # Should return the default image if no filename is provided
    assert ensure_aircraft_image(None) == 'images/aircraft/default.jpg'
    assert ensure_aircraft_image('') == 'images/aircraft/default.jpg'

def test_ensure_aircraft_image_existing(tmp_path, monkeypatch):
    # Create a dummy image file >1KB
    test_dir = tmp_path / "static" / "images" / "aircraft"
    test_dir.mkdir(parents=True, exist_ok=True)
    fname = "test_existing.jpg"
    fpath = test_dir / fname
    with open(fpath, "wb") as f:
        f.write(b"x" * 2048)
    orig_exists = os.path.exists
    orig_getsize = os.path.getsize
    monkeypatch.setattr(os.path, "exists", lambda path: str(fpath) in path or orig_exists(path))
    monkeypatch.setattr(os.path, "getsize", lambda path: 2048 if str(fpath) in path else orig_getsize(path))
    monkeypatch.setattr(os.path, "dirname", lambda path: str(tmp_path))
    # Should return the correct path for an existing file
    result = ensure_aircraft_image(fname)
    assert result == f'images/aircraft/{fname}'
    # Validate that the file is >0 bytes (real image returned)
    assert fpath.exists()
    assert fpath.stat().st_size > 0

def test_ensure_aircraft_image_fetch(monkeypatch, tmp_path):
    # Simulate Wikimedia returning an image url and valid image content
    class DummyResp:
        def __init__(self, json_data=None, content=None):
            self._json = json_data
            self.content = content
        def json(self):
            return self._json
    def dummy_requests_get(url, timeout=None):
        if 'wikimedia' in url:
            return DummyResp(json_data={
                'query': {'pages': {'1': {'imageinfo': [{'url': 'http://dummy/image.jpg'}]}}}
            })
        elif 'dummy/image.jpg' in url:
            return DummyResp(content=b"z" * 2048)
        raise RuntimeError("Unexpected url")
    monkeypatch.setattr("requests.get", dummy_requests_get)
    # Patch os.path to use tmp_path
    test_dir = tmp_path / "static" / "images" / "aircraft"
    test_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(os.path, "dirname", lambda path: str(tmp_path))
    fname = "fetched.jpg"
    result = ensure_aircraft_image(fname, make="TestMake", model="TestModel")
    assert result == f'images/aircraft/{fname}'
    # File should exist and be >0 bytes
    fpath = test_dir / fname
    assert fpath.exists()
    assert fpath.stat().st_size > 0

def test_ensure_aircraft_image_fetch_fail(monkeypatch, tmp_path):
    # Simulate Wikimedia returning no results and requests raising an error
    def dummy_requests_get(url, timeout=None):
        raise Exception("fail")
    monkeypatch.setattr("requests.get", dummy_requests_get)
    monkeypatch.setattr(os.path, "dirname", lambda path: str(tmp_path))
    fname = "fail.jpg"
    result = ensure_aircraft_image(fname, make="TestMake", model="TestModel")
    assert result == 'images/aircraft/default.jpg'
