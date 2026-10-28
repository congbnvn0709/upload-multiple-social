# Multi-Platform Social Video Publisher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local personal web application with a Studio Split-Screen interface to generate platform-tailored video captions using AI and publish short-form vertical videos sequentially to TikTok, Threads, Facebook (Profile & Fanpage), and YouTube via Playwright browser automation.

**Architecture:** A FastAPI Python backend controls Playwright browser automation with a persistent Chromium user profile and integrates with an LLM for copy generation; a React + Vite + Tailwind CSS frontend provides a side-by-side video preview, caption customizer, account status inspector, and real-time log terminal over WebSockets.

**Tech Stack:** Python 3.10+, FastAPI, Uvicorn, Playwright, google-genai / openai, React, Vite, Tailwind CSS, Lucide React.

**Spec:** `docs/superpowers/specs/2026-10-28-social-video-publisher-design.md`

## Global Constraints
- Target OS: macOS (Darwin arm64/x86_64).
- Single-user local execution: No external auth/database requirements; persistent state resides in `.browser_profile` and local config.
- Browser Automation Mode: Must run headed (`headless=False`) by default to prevent anti-bot detection and allow human captcha/2FA solving.
- Facebook Destination: Support user toggle between Personal Profile Reel (`facebook.com/reel/create`), Fanpage Reel, or both.
- Sequential Queue: Uploads must execute one platform after another to avoid profile lock collisions (`SingletonLock`) and network congestion.

## Review Focus
1. **Video format compatibility:** A non-MP4 or corrupted file is dropped into the uploader; expected behavior: clear UI error message and rejection before passing to Playwright.
2. **Session expiration / Not logged in:** A platform's session cookie expired; expected behavior: bot detects the login screen, pauses with a clear log `"Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại"`, and does not crash the entire queue.
3. **Captcha trigger during upload:** TikTok or Facebook displays a slider or visual captcha; expected behavior: headed browser remains open, log notifies user `"Phát hiện mã xác minh trên trình duyệt, hãy thao tác trên màn hình"`, and waits up to 60s for user completion.
4. **Missing or invalid AI API key:** User requests AI captions without setting `GEMINI_API_KEY`; expected behavior: fallback graceful error asking for API key instead of 500 internal server error.
5. **DOM selector changes on social networks:** A button selector fails because a platform updated its UI; expected behavior: individual platform marks failure with screenshot captured to `logs/`, while other queued platforms continue without aborting.

---

### Task 1: Project Scaffolding & Directory Structure

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/main.py`
- Create: `backend/config.py`
- Create: `frontend/package.json`
- Create: `run.sh`
- Test: `tests/test_scaffolding.py`

**Interfaces:**
- Produces: Base running FastAPI backend and React frontend development server skeleton.

- [ ] **Step 1: Write test for backend app initialization and health check**

```python
# tests/test_scaffolding.py
from fastapi.testclient import TestClient
from backend.main import app

def test_health_check():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_scaffolding.py`  
Expected: FAIL with `ModuleNotFoundError: No module named 'backend'`

- [ ] **Step 3: Implement backend scaffolding and health endpoint**

Create `backend/requirements.txt` with `fastapi`, `uvicorn`, `playwright`, `google-genai`, `python-dotenv`, `pydantic`.  
Create `backend/config.py` defining file upload paths (`temp_uploads/`) and browser profile directory (`.browser_profile/`).  
Create `backend/main.py` with FastAPI app and `GET /api/health` endpoint.  
Create root `run.sh` to initialize Python venv, install requirements, and run development servers.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_scaffolding.py`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/ requirements.txt run.sh tests/test_scaffolding.py
git commit -m "feat: initialize backend scaffolding and health check"
```

---

### Task 2: Video Staging & Metadata API

**Files:**
- Create: `backend/services/video_service.py`
- Modify: `backend/main.py`
- Test: `tests/test_video_service.py`

**Interfaces:**
- Produces: `POST /api/upload` endpoint accepting multipart file, returning `{ filename: str, path: str, size: int, stream_url: str }`.

- [ ] **Step 1: Write test for video upload and validation**

```python
# tests/test_video_service.py
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
    assert data["size"] > 0

def test_upload_invalid_file_type():
    client = TestClient(app)
    fake_text = io.BytesIO(b"not a video")
    response = client.post(
        "/api/upload",
        files={"file": ("test.txt", fake_text, "text/plain")}
    )
    assert response.status_code == 400
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_video_service.py`  
Expected: FAIL with `404 Not Found`

- [ ] **Step 3: Implement `backend/services/video_service.py` and route in `main.py`**

Handle saving uploaded video to `temp_uploads/`, validate `.mp4` and `.mov` extensions, mount static file route `/media/` for native HTML5 video preview streaming.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_video_service.py`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/video_service.py backend/main.py tests/test_video_service.py
git commit -m "feat: add video upload and streaming API"
```

---

### Task 3: AI Caption Generation Service

**Files:**
- Create: `backend/services/ai_service.py`
- Modify: `backend/main.py`
- Test: `tests/test_ai_service.py`

**Interfaces:**
- Produces: `POST /api/ai/generate` taking `{ topic: str }` and returning platform-optimized captions:
  ```json
  {
    "tiktok": { "caption": str, "hashtags": list[str] },
    "threads": { "caption": str, "hashtags": list[str] },
    "facebook": { "caption": str, "hashtags": list[str] },
    "youtube": { "title": str, "description": str, "tags": list[str] }
  }
  ```

- [ ] **Step 1: Write test for AI caption schema and fallback generation**

```python
# tests/test_ai_service.py
from fastapi.testclient import TestClient
from backend.main import app

def test_ai_generate_schema(monkeypatch):
    from backend.services import ai_service
    # Mock LLM response to verify formatting without calling live API in unit tests
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
    assert "tiktok" in res and "caption" in res["tiktok"]
    assert "threads" in res
    assert "facebook" in res
    assert "youtube" in res and "title" in res["youtube"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ai_service.py`  
Expected: FAIL with `404 Not Found`

- [ ] **Step 3: Implement `backend/services/ai_service.py` and route**

Implement prompt engineering for Gemini/OpenAI API:
- System prompt setting individual style profiles for TikTok, Threads, Facebook, and YouTube Shorts.
- Handle missing API key gracefully with mock/template generator so user can still test without an API key immediately.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ai_service.py`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/ai_service.py backend/main.py tests/test_ai_service.py
git commit -m "feat: implement AI caption generation service"
```

---

### Task 4: Playwright Profile & Session Manager

**Files:**
- Create: `backend/services/session_service.py`
- Modify: `backend/main.py`
- Test: `tests/test_session_service.py`

**Interfaces:**
- Produces:
  - `GET /api/accounts/status` -> `{ tiktok: bool, threads: bool, facebook: bool, youtube: bool }`
  - `POST /api/accounts/open-login` taking `{ platform: str }` -> launches headed Chromium pointing to the platform's login page using persistent context.

- [ ] **Step 1: Write test for account status check**

```python
# tests/test_session_service.py
from fastapi.testclient import TestClient
from backend.main import app

def test_account_status_endpoint():
    client = TestClient(app)
    response = client.get("/api/accounts/status")
    assert response.status_code == 200
    data = response.json()
    for platform in ["tiktok", "threads", "facebook", "youtube"]:
        assert platform in data
        assert isinstance(data[platform], bool)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_session_service.py`  
Expected: FAIL with `404 Not Found`

- [ ] **Step 3: Implement `backend/services/session_service.py`**

- Read cookies and storage state from `.browser_profile/` to determine authenticated status.
- Implement `open_login_window(platform: str)` using `playwright.chromium.launch_persistent_context(..., headless=False)` so user can log in and persist sessions.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_session_service.py`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/session_service.py backend/main.py tests/test_session_service.py
git commit -m "feat: add persistent browser session and login manager"
```

---

### Task 5: Platform Uploaders (Playwright Automation)

**Files:**
- Create: `backend/uploaders/base.py`
- Create: `backend/uploaders/tiktok.py`
- Create: `backend/uploaders/threads.py`
- Create: `backend/uploaders/facebook.py`
- Create: `backend/uploaders/youtube.py`
- Test: `tests/test_uploaders.py`

**Interfaces:**
- Produces: Standardized `Uploader` interface:
  ```python
  class BaseUploader:
      async def upload(self, page: Page, video_path: str, metadata: dict, log_callback: Callable) -> bool
  ```

- [ ] **Step 1: Write test for uploader registry and interface contract**

```python
# tests/test_uploaders.py
from backend.uploaders.base import get_uploader
from backend.uploaders.tiktok import TikTokUploader
from backend.uploaders.facebook import FacebookUploader

def test_uploader_registry():
    uploader = get_uploader("tiktok")
    assert isinstance(uploader, TikTokUploader)
    fb_uploader = get_uploader("facebook")
    assert isinstance(fb_uploader, FacebookUploader)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_uploaders.py`  
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement uploaders with resilient selectors and humanized typing**

- `tiktok.py`: target `tiktok.com/creator-center/upload`, upload file input, caption editor with `#hashtags`, click post.
- `threads.py`: target `threads.net`, open compose dialog, upload video, insert text caption, click post.
- `facebook.py`: support both `target="profile"` (`facebook.com/reel/create`) and `target="fanpage"` (persona switch / reels composer).
- `youtube.py`: target `studio.youtube.com`, upload file, fill Title (<100 chars), Description, mark not for kids, publish as Public.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_uploaders.py`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/uploaders/ tests/test_uploaders.py
git commit -m "feat: implement platform uploaders for TikTok, Threads, Facebook, YouTube"
```

---

### Task 6: Publishing Orchestrator & Live WebSocket Logging

**Files:**
- Create: `backend/services/publisher.py`
- Modify: `backend/main.py`
- Test: `tests/test_publisher.py`

**Interfaces:**
- Produces:
  - `POST /api/publish`: starts background task processing platforms sequentially.
  - `WebSocket /ws/logs`: real-time log event streaming `{ platform: str, status: "info" | "success" | "error", message: str }`.

- [ ] **Step 1: Write test for publish dispatch and sequential queue order**

```python
# tests/test_publisher.py
from fastapi.testclient import TestClient
from backend.main import app

def test_publish_validation():
    client = TestClient(app)
    # Empty payload should fail validation
    res = client.post("/api/publish", json={})
    assert res.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_publisher.py`  
Expected: FAIL with `404 Not Found`

- [ ] **Step 3: Implement sequential publishing orchestrator and WebSocket manager**

- Queue selected platforms sequentially in one persistent browser session.
- Stream status events before, during, and after each platform upload.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_publisher.py`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/publisher.py backend/main.py tests/test_publisher.py
git commit -m "feat: implement publishing orchestrator and WebSocket logs"
```

---

### Task 7: Frontend Studio Split-Screen UI

**Files:**
- Create: `frontend/src/App.jsx`
- Create: `frontend/src/components/VideoUploadSection.jsx`
- Create: `frontend/src/components/AIPromptSection.jsx`
- Create: `frontend/src/components/PlatformCard.jsx`
- Create: `frontend/src/components/AccountStatusHeader.jsx`
- Create: `frontend/src/components/LiveLogsDrawer.jsx`
- Test: `frontend/src/App.test.jsx`

**Interfaces:**
- Consumes: All backend REST endpoints (`/api/upload`, `/api/ai/generate`, `/api/accounts/*`, `/api/publish`) and WebSocket `/ws/logs`.

- [ ] **Step 1: Write frontend component render test**

Create `frontend/src/App.test.jsx` verifying render of Left Column (Video + AI prompt) and Right Column (Platform Cards + Publish action).

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test` in `frontend/`  
Expected: FAIL

- [ ] **Step 3: Implement Studio Split-Screen layout with Tailwind CSS**

- Left panel: Drag-and-drop zone with video player and topic textarea + AI generate button.
- Right panel: 4 platform cards with toggle checkbox, caption textarea, tag chips, and Facebook Profile vs Fanpage radio selection.
- Bottom bar: Status badges, "Đăng Lên Nền Tảng Đã Chọn" button, and collapsible live log drawer.

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test` in `frontend/`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: implement studio split-screen frontend UI"
```

---

### Task 8: End-to-End Integration & Launch Script

**Files:**
- Modify: `run.sh`
- Create: `README.md`
- Test: `tests/test_e2e_smoke.py`

**Interfaces:**
- Produces: Single `./run.sh` launch script that starts backend and frontend, checks Playwright browsers, and opens browser window.

- [ ] **Step 1: Write smoke test verifying API and static bundle accessibility**

```python
# tests/test_e2e_smoke.py
from fastapi.testclient import TestClient
from backend.main import app

def test_e2e_api_health():
    client = TestClient(app)
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/accounts/status").status_code == 200
```

- [ ] **Step 2: Run smoke test**

Run: `pytest tests/test_e2e_smoke.py`  
Expected: PASS

- [ ] **Step 3: Update `run.sh` and write `README.md`**

Ensure `./run.sh` checks Python venv, installs Playwright Chromium (`playwright install chromium`), starts FastAPI on port 8000 and Vite on port 5173, and opens browser at `http://localhost:5173`.

- [ ] **Step 4: Commit**

```bash
git add run.sh README.md tests/test_e2e_smoke.py
git commit -m "chore: complete e2e integration and launch script"
```
