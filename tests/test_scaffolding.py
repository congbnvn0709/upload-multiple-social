from fastapi.testclient import TestClient
from backend.main import app
from backend.config import UPLOAD_DIR, BROWSER_PROFILE_DIR, LOGS_DIR

def test_health_check():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_config_paths():
    assert UPLOAD_DIR.exists()
    assert BROWSER_PROFILE_DIR.exists()
    assert LOGS_DIR.exists()
