import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.publisher import ConnectionManager, PublishRequest, PlatformConfig


def test_publish_validation_empty():
    client = TestClient(app)
    # Empty payload should fail validation with 422 Unprocessable Entity
    res = client.post("/api/publish", json={})
    assert res.status_code == 422


def test_publish_nonexistent_video(tmp_path):
    client = TestClient(app)
    fake_path = str(tmp_path / "nonexistent.mp4")
    res = client.post(
        "/api/publish",
        json={
            "video_path": fake_path,
            "platforms": {
                "tiktok": {"enabled": True, "caption": "Test video", "hashtags": ["test"]}
            },
        },
    )
    assert res.status_code == 400
    assert "not found" in res.json()["detail"].lower()


def test_publish_success_starts_background_task(tmp_path):
    test_video = tmp_path / "video.mp4"
    test_video.write_bytes(b"dummy video content")

    client = TestClient(app)
    with patch("backend.main.run_publishing_pipeline", new_callable=AsyncMock) as mock_pipeline:
        res = client.post(
            "/api/publish",
            json={
                "video_path": str(test_video),
                "platforms": {
                    "tiktok": {"enabled": True, "caption": "TikTok test"},
                    "youtube": {"enabled": True, "title": "YouTube test"},
                    "threads": {"enabled": False, "caption": "Disabled test"},
                },
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "queued"
        assert set(data["platforms"]) == {"tiktok", "youtube"}
        # Pipeline should have been called in background
        mock_pipeline.assert_called_once()


def test_websocket_connection_and_broadcast():
    client = TestClient(app)
    with client.websocket_connect("/ws/logs") as websocket:
        # Broadcast a log via connection manager
        from backend.services.publisher import manager
        
        # Run broadcast
        asyncio.run(
            manager.broadcast_log(
                platform="tiktok",
                status="info",
                message="Starting upload...",
            )
        )
        data = websocket.receive_json()
        assert data["platform"] == "tiktok"
        assert data["status"] == "info"
        assert data["message"] == "Starting upload..."
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_publishing_pipeline_sequential_execution(tmp_path):
    test_video = tmp_path / "sample.mp4"
    test_video.write_bytes(b"video bytes")

    req = PublishRequest(
        video_path=str(test_video),
        platforms={
            "tiktok": PlatformConfig(enabled=True, caption="Caption 1"),
            "facebook": PlatformConfig(enabled=True, caption="Caption 2"),
            "threads": PlatformConfig(enabled=False),
        },
    )

    execution_order = []

    mock_tiktok = AsyncMock()
    async def tiktok_upload(*args, **kwargs):
        execution_order.append("tiktok")
        log_cb = kwargs.get("log_callback")
        if log_cb:
            log_cb("tiktok progress", "info")
        return True
    mock_tiktok.upload = tiktok_upload

    mock_facebook = AsyncMock()
    async def fb_upload(*args, **kwargs):
        execution_order.append("facebook")
        return True
    mock_facebook.upload = fb_upload

    def get_uploader_mock(platform: str):
        if platform == "tiktok":
            return mock_tiktok
        if platform == "facebook":
            return mock_facebook
        raise ValueError(f"Unknown platform: {platform}")

    mock_page = AsyncMock()
    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.close = AsyncMock()

    mock_pw = AsyncMock()
    mock_pw.chromium.launch_persistent_context = AsyncMock(return_value=mock_context)

    with patch("backend.services.publisher.async_playwright") as mock_apw, \
         patch("backend.services.publisher.get_uploader", side_effect=get_uploader_mock), \
         patch("backend.services.publisher.manager.broadcast_log", new_callable=AsyncMock) as mock_broadcast:
        
        mock_apw.return_value.__aenter__.return_value = mock_pw

        from backend.services.publisher import run_publishing_pipeline
        await run_publishing_pipeline(req)

        assert execution_order == ["tiktok", "facebook"]
        mock_context.close.assert_called_once()
        assert mock_broadcast.call_count >= 4  # Start & Success for tiktok + fb


@pytest.mark.asyncio
async def test_publishing_pipeline_continues_on_failure(tmp_path):
    test_video = tmp_path / "sample.mp4"
    test_video.write_bytes(b"video bytes")

    req = PublishRequest(
        video_path=str(test_video),
        platforms={
            "tiktok": PlatformConfig(enabled=True, caption="Caption 1"),
            "youtube": PlatformConfig(enabled=True, title="Title 2"),
        },
    )

    mock_tiktok = AsyncMock()
    mock_tiktok.upload.side_effect = RuntimeError("TikTok upload crashed!")

    mock_youtube = AsyncMock()
    mock_youtube.upload.return_value = True

    def get_uploader_mock(platform: str):
        if platform == "tiktok":
            return mock_tiktok
        if platform == "youtube":
            return mock_youtube
        raise ValueError(f"Unknown platform: {platform}")

    mock_page = AsyncMock()
    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.close = AsyncMock()

    mock_pw = AsyncMock()
    mock_pw.chromium.launch_persistent_context = AsyncMock(return_value=mock_context)

    with patch("backend.services.publisher.async_playwright") as mock_apw, \
         patch("backend.services.publisher.get_uploader", side_effect=get_uploader_mock), \
         patch("backend.services.publisher.manager.broadcast_log", new_callable=AsyncMock) as mock_broadcast:
        
        mock_apw.return_value.__aenter__.return_value = mock_pw

        from backend.services.publisher import run_publishing_pipeline
        await run_publishing_pipeline(req)

        # YouTube should still be executed even though TikTok raised RuntimeError
        mock_youtube.upload.assert_called_once()
        mock_context.close.assert_called_once()
        # Verify an error log was broadcasted for tiktok
        error_calls = [
            call for call in mock_broadcast.call_args_list
            if call.kwargs.get("status") == "error" or (len(call.args) > 1 and call.args[1] == "error")
        ]
        assert len(error_calls) >= 1
