import asyncio
import inspect
import os
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from backend.config import UPLOAD_DIR, BROWSER_PROFILE_DIR
from backend.services.video_service import stage_uploaded_video
from backend.services.ai_service import (
    GenerateCaptionsRequest,
    generate_captions_for_topic,
)
from backend.services.session_service import (
    LOGIN_URLS,
    get_account_status,
    open_login_window,
)
from backend.services.publisher import (
    PublishRequest,
    manager,
    run_publishing_pipeline,
)

app = FastAPI(
    title="Multi-Platform Social Video Publisher",
    description="Local web app to publish short-form vertical videos sequentially via Playwright",
    version="1.0.0"
)

# Enable CORS for local React development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static file route for native HTML5 video streaming and preview
app.mount("/media", StaticFiles(directory=str(UPLOAD_DIR)), name="media")


@app.get("/api/health")
async def health_check():
    """Health check endpoint to verify backend server is running."""
    return {"status": "ok"}


@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload and stage a video file for preview and publishing."""
    return await stage_uploaded_video(file)


@app.post("/api/ai/generate")
async def generate_captions(payload: GenerateCaptionsRequest):
    """Generate platform-tailored captions, hashtags, and titles for a video topic."""
    result = await asyncio.to_thread(generate_captions_for_topic, payload.topic)
    if inspect.isawaitable(result):
        result = await result
    return result


class OpenLoginRequest(BaseModel):
    platform: str


@app.get("/api/accounts/status")
async def get_accounts_status():
    """Retrieve authentication status across supported social platforms."""
    return await asyncio.to_thread(get_account_status)


@app.post("/api/accounts/open-login")
async def open_login(payload: OpenLoginRequest):
    """Launch persistent headed browser window for interactive account login."""
    platform = payload.platform.strip().lower()
    if platform not in LOGIN_URLS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported platform '{payload.platform}'. Supported platforms: {', '.join(LOGIN_URLS.keys())}",
        )
    open_login_window(platform)
    return {"status": "opened", "platform": platform}


@app.post("/api/publish")
async def publish_video(payload: PublishRequest, background_tasks: BackgroundTasks):
    """
    Validates publishing request and starts background sequential pipeline.
    """
    if not os.path.exists(payload.video_path):
        raise HTTPException(
            status_code=400,
            detail=f"Video file not found at path: {payload.video_path}",
        )

    enabled_platforms = [
        plat for plat, config in payload.platforms.items() if config.enabled
    ]

    background_tasks.add_task(run_publishing_pipeline, payload)
    return {
        "status": "queued",
        "platforms": enabled_platforms,
    }


@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """
    Real-time log streaming WebSocket endpoint for publishing events.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and listen for client ping or close
            await websocket.receive_text()
    except (WebSocketDisconnect, Exception):
        manager.disconnect(websocket)



