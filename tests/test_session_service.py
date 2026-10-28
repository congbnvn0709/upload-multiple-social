import json
import sqlite3
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.session_service import (
    get_account_status,
    open_login_window,
    LOGIN_URLS,
)


def test_account_status_endpoint():
    """Test GET /api/accounts/status returns boolean statuses for all platforms."""
    client = TestClient(app)
    response = client.get("/api/accounts/status")
    assert response.status_code == 200
    data = response.json()
    for platform in ["tiktok", "threads", "facebook", "youtube"]:
        assert platform in data
        assert isinstance(data[platform], bool)


def test_open_login_endpoint_success():
    """Test POST /api/accounts/open-login with valid platform triggers browser launch."""
    client = TestClient(app)
    with patch("backend.main.open_login_window") as mock_open:
        response = client.post("/api/accounts/open-login", json={"platform": "tiktok"})
        assert response.status_code == 200
        assert response.json() == {"status": "opened", "platform": "tiktok"}
        mock_open.assert_called_once_with("tiktok")


def test_open_login_endpoint_invalid_platform():
    """Test POST /api/accounts/open-login with unsupported platform returns 400."""
    client = TestClient(app)
    response = client.post("/api/accounts/open-login", json={"platform": "twitter_x"})
    assert response.status_code == 400
    assert "Unsupported platform" in response.json()["detail"]


def test_get_account_status_empty_dir(tmp_path):
    """Test get_account_status returns all False for an empty directory."""
    status = get_account_status(profile_dir=tmp_path)
    assert status == {
        "tiktok": False,
        "threads": False,
        "facebook": False,
        "youtube": False,
    }


def test_get_account_status_with_storage_state(tmp_path):
    """Test get_account_status detects domains present in storage_state.json."""
    state = {
        "cookies": [
            {"name": "sessionid", "domain": ".tiktok.com", "value": "xyz"},
            {"name": "sessionid", "domain": ".threads.net", "value": "abc"},
        ],
        "origins": [],
    }
    state_file = tmp_path / "storage_state.json"
    state_file.write_text(json.dumps(state), encoding="utf-8")

    status = get_account_status(profile_dir=tmp_path)
    assert status["tiktok"] is True
    assert status["threads"] is True
    assert status["facebook"] is False
    assert status["youtube"] is False


def test_get_account_status_with_sqlite_cookies(tmp_path):
    """Test get_account_status detects domains present in Chromium SQLite Cookies DB."""
    default_dir = tmp_path / "Default"
    default_dir.mkdir(parents=True)
    db_file = default_dir / "Cookies"

    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE cookies (host_key TEXT, name TEXT, value TEXT)")
    conn.execute("INSERT INTO cookies VALUES ('.facebook.com', 'c_user', '123')")
    conn.execute("INSERT INTO cookies VALUES ('.youtube.com', 'LOGIN_INFO', '456')")
    conn.commit()
    conn.close()

    status = get_account_status(profile_dir=tmp_path)
    assert status["facebook"] is True
    assert status["youtube"] is True
    assert status["tiktok"] is False
    assert status["threads"] is False


def test_open_login_window_unsupported_raises():
    """Test open_login_window raises ValueError for unsupported platform."""
    with pytest.raises(ValueError, match="Unsupported platform"):
        open_login_window("unsupported_xyz")


def test_open_login_window_launches_persistent_context(tmp_path):
    """Test open_login_window launches persistent context with correct URL."""
    with patch("backend.services.session_service._run_browser") as mock_run:
        thread = open_login_window("youtube", profile_dir=tmp_path, block=False)
        assert thread is not None
        thread.join(timeout=2)
        mock_run.assert_called_once_with("youtube", False, tmp_path)
