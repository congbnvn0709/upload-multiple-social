import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from backend.main import app
from backend.services import ai_service


def test_ai_generate_schema(monkeypatch):
    """Verify endpoint schema with mocked generate_captions_for_topic as specified in task brief."""
    def mock_generate(topic: str):
        return {
            "tiktok": {"caption": f"Hook: {topic} #trend", "hashtags": ["#trend", "#viral"]},
            "threads": {"caption": f"What do you think about {topic}?", "hashtags": ["#thoughts"]},
            "facebook": {"caption": f"Story about {topic}", "hashtags": ["#story"]},
            "youtube": {"title": f"{topic} in 60s", "description": f"Full details on {topic}", "tags": ["shorts", "tech"]}
        }
    monkeypatch.setattr(ai_service, "generate_captions_for_topic", mock_generate)

    client = TestClient(app)
    response = client.post("/api/ai/generate", json={"topic": "Học AI từ đâu"})
    assert response.status_code == 200
    res = response.json()
    assert "tiktok" in res and "caption" in res["tiktok"] and "hashtags" in res["tiktok"]
    assert "threads" in res and "caption" in res["threads"] and "hashtags" in res["threads"]
    assert "facebook" in res and "caption" in res["facebook"] and "hashtags" in res["facebook"]
    assert "youtube" in res and "title" in res["youtube"] and "description" in res["youtube"] and "tags" in res["youtube"]


def test_ai_generate_fallback_when_no_api_key(monkeypatch):
    """When GEMINI_API_KEY is unset or empty, should return valid template captions without throwing 500."""
    monkeypatch.setattr(ai_service, "GEMINI_API_KEY", "")

    client = TestClient(app)
    response = client.post("/api/ai/generate", json={"topic": "Tự học Python cơ bản"})
    assert response.status_code == 200
    data = response.json()

    # Check TikTok structure and fallback contents
    assert "tiktok" in data
    assert "caption" in data["tiktok"]
    assert "Tự học Python cơ bản" in data["tiktok"]["caption"]
    assert isinstance(data["tiktok"]["hashtags"], list)
    assert len(data["tiktok"]["hashtags"]) > 0

    # Check Threads structure
    assert "threads" in data
    assert "caption" in data["threads"]
    assert "Tự học Python cơ bản" in data["threads"]["caption"]
    assert isinstance(data["threads"]["hashtags"], list)

    # Check Facebook structure
    assert "facebook" in data
    assert "caption" in data["facebook"]
    assert "Tự học Python cơ bản" in data["facebook"]["caption"]
    assert isinstance(data["facebook"]["hashtags"], list)

    # Check YouTube Shorts structure
    assert "youtube" in data
    assert "title" in data["youtube"]
    assert "description" in data["youtube"]
    assert "tags" in data["youtube"]
    assert "Tự học Python cơ bản" in data["youtube"]["title"]
    assert isinstance(data["youtube"]["tags"], list)


def test_ai_generate_fallback_on_gemini_error(monkeypatch):
    """When GEMINI_API_KEY is present but API call throws an exception, fall back gracefully to templates."""
    monkeypatch.setattr(ai_service, "GEMINI_API_KEY", "fake_key_123")

    mock_client_instance = MagicMock()
    mock_client_instance.models.generate_content.side_effect = Exception("API quota exceeded or network down")

    def mock_get_gemini_client():
        return mock_client_instance

    monkeypatch.setattr(ai_service, "get_gemini_client", mock_get_gemini_client)

    client = TestClient(app)
    response = client.post("/api/ai/generate", json={"topic": "Cách làm giàu nhanh"})
    assert response.status_code == 200
    data = response.json()
    assert "tiktok" in data
    assert "threads" in data
    assert "facebook" in data
    assert "youtube" in data
    assert "Cách làm giàu nhanh" in data["tiktok"]["caption"]


def test_ai_generate_gemini_live_mock_success(monkeypatch):
    """When GEMINI_API_KEY is present and call succeeds, return parsed structured captions."""
    monkeypatch.setattr(ai_service, "GEMINI_API_KEY", "fake_key_123")

    mock_response = MagicMock()
    mock_response.text = '''{
        "tiktok": {"caption": "Bật mí mẹo học AI cực đỉnh! #ai", "hashtags": ["#ai", "#techtips"]},
        "threads": {"caption": "Bạn đã áp dụng AI vào công việc chưa?", "hashtags": ["#tech"]},
        "facebook": {"caption": "Tổng hợp kinh nghiệm thực chiến với AI", "hashtags": ["#congnghe"]},
        "youtube": {"title": "Lộ trình AI 2026", "description": "Xem chi tiết hướng dẫn AI", "tags": ["ai", "learning"]}
    }'''

    mock_client_instance = MagicMock()
    mock_client_instance.models.generate_content.return_value = mock_response

    monkeypatch.setattr(ai_service, "get_gemini_client", lambda: mock_client_instance)

    client = TestClient(app)
    response = client.post("/api/ai/generate", json={"topic": "Mẹo học AI"})
    assert response.status_code == 200
    data = response.json()
    assert data["tiktok"]["caption"] == "Bật mí mẹo học AI cực đỉnh! #ai"
    assert data["youtube"]["title"] == "Lộ trình AI 2026"


def test_ai_generate_validation_error():
    """Missing or empty topic should return 422 Unprocessable Entity."""
    client = TestClient(app)
    # Missing topic
    res1 = client.post("/api/ai/generate", json={})
    assert res1.status_code == 422

    # Blank topic
    res2 = client.post("/api/ai/generate", json={"topic": "   "})
    assert res2.status_code == 422
