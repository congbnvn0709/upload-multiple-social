import io
from fastapi.testclient import TestClient
from backend.main import app

def test_upload_valid_video():
    client = TestClient(app)
    fake_video = io.BytesIO(b"fake mp4 video bytes")
    response = client.post(
        "/api/upload",
        files={"file": ("test.mp4", fake_video, "video/mp4")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.mp4"
    assert "stream_url" in data
    assert data["stream_url"] == "/media/test.mp4"
    assert "path" in data
    assert data["size"] == len(b"fake mp4 video bytes")

    # Verify static file streaming endpoint
    media_response = client.get(data["stream_url"])
    assert media_response.status_code == 200
    assert media_response.content == b"fake mp4 video bytes"

def test_upload_valid_mov_video():
    client = TestClient(app)
    fake_video = io.BytesIO(b"fake mov video bytes")
    response = client.post(
        "/api/upload",
        files={"file": ("test.mov", fake_video, "video/quicktime")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.mov"
    assert data["stream_url"] == "/media/test.mov"
    assert data["size"] == len(b"fake mov video bytes")

def test_upload_invalid_file_type():
    client = TestClient(app)
    fake_text = io.BytesIO(b"not a video")
    response = client.post(
        "/api/upload",
        files={"file": ("test.txt", fake_text, "text/plain")}
    )
    assert response.status_code == 400
    assert "detail" in response.json()

def test_upload_uppercase_extension():
    client = TestClient(app)
    fake_video = io.BytesIO(b"fake uppercase mp4 video")
    response = client.post(
        "/api/upload",
        files={"file": ("TEST_UPPER.MP4", fake_video, "video/mp4")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "TEST_UPPER.MP4"
    assert data["stream_url"] == "/media/TEST_UPPER.MP4"
    assert data["size"] == len(b"fake uppercase mp4 video")

