import asyncio
import io
import json
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.publisher import manager


def test_e2e_api_health():
    """Verify backend health check and account status endpoints."""
    client = TestClient(app)
    health_resp = client.get("/api/health")
    assert health_resp.status_code == 200
    assert health_resp.json() == {"status": "ok"}

    accounts_resp = client.get("/api/accounts/status")
    assert accounts_resp.status_code == 200
    accounts_data = accounts_resp.json()
    assert isinstance(accounts_data, dict)
    for platform in ["tiktok", "threads", "facebook", "youtube"]:
        assert platform in accounts_data
        assert isinstance(accounts_data[platform], bool)


def test_e2e_video_upload_validation():
    """Verify video upload validation for valid media and invalid file types."""
    client = TestClient(app)

    # 1. Invalid file rejection
    invalid_file = io.BytesIO(b"Hello world, not a video")
    resp_invalid = client.post(
        "/api/upload",
        files={"file": ("notes.txt", invalid_file, "text/plain")},
    )
    assert resp_invalid.status_code == 400
    assert "detail" in resp_invalid.json()

    # 2. Valid MP4 upload acceptance & preview URL
    valid_video = io.BytesIO(b"fake e2e mp4 video bytes")
    resp_valid = client.post(
        "/api/upload",
        files={"file": ("smoke_test.mp4", valid_video, "video/mp4")},
    )
    assert resp_valid.status_code == 200
    data = resp_valid.json()
    assert data["filename"] == "smoke_test.mp4"
    assert data["stream_url"] == "/media/smoke_test.mp4"
    assert "path" in data

    # 3. Verify static streaming
    media_resp = client.get(data["stream_url"])
    assert media_resp.status_code == 200
    assert media_resp.content == b"fake e2e mp4 video bytes"


def test_e2e_ai_generate_fallback():
    """Verify AI caption generation with graceful fallback when API key is missing or offline."""
    client = TestClient(app)
    resp = client.post("/api/ai/generate", json={"topic": "Top 3 productivity hacks for developers"})
    assert resp.status_code == 200
    data = resp.json()

    for platform in ["tiktok", "threads", "facebook", "youtube"]:
        assert platform in data

    assert "caption" in data["tiktok"]
    assert "hashtags" in data["tiktok"]
    assert "caption" in data["threads"]
    assert "caption" in data["facebook"]
    assert "title" in data["youtube"]
    assert "description" in data["youtube"]


def test_e2e_websocket_connection():
    """Verify real-time WebSocket connection and log broadcasting."""
    client = TestClient(app)
    with client.websocket_connect("/ws/logs") as websocket:
        # Broadcast a test log message via the connection manager
        asyncio.run(
            manager.broadcast_log(
                platform="tiktok",
                status="success",
                message="E2E smoke test log message",
            )
        )

        received_raw = websocket.receive_text()
        received = json.loads(received_raw)
        assert received["platform"] == "tiktok"
        assert received["status"] == "success"
        assert received["message"] == "E2E smoke test log message"
        assert "timestamp" in received
