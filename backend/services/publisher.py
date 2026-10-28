import asyncio
import datetime
import inspect
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from playwright.async_api import async_playwright

from backend.config import BROWSER_PROFILE_DIR, HEADLESS
from backend.uploaders.base import get_uploader

logger = logging.getLogger(__name__)


class PlatformConfig(BaseModel):
    enabled: bool = True
    caption: Optional[str] = ""
    hashtags: Optional[List[str]] = Field(default_factory=list)
    title: Optional[str] = ""  # For YouTube
    description: Optional[str] = ""  # For YouTube
    tags: Optional[List[str]] = Field(default_factory=list)  # For YouTube
    target: Optional[str] = "profile"  # For Facebook ("profile" or "fanpage")
    visibility: Optional[str] = "public"  # For YouTube


class PublishRequest(BaseModel):
    video_path: str
    platforms: Dict[str, PlatformConfig]


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts real-time logs."""

    def __init__(self):
        self.active_connections: List[Any] = []

    async def connect(self, websocket: Any):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: Any):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_log(
        self,
        platform: str,
        status: str,
        message: str,
    ):
        """
        Broadcasts a log message to all connected WebSocket clients.
        Payload format:
        {
            "platform": str,
            "status": "info" | "success" | "error",
            "message": str,
            "timestamp": str (ISO 8601)
        }
        """
        payload = {
            "platform": platform,
            "status": status,
            "message": message,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        disconnected = []
        for connection in self.active_connections:
            try:
                res = connection.send_json(payload)
                if inspect.isawaitable(res):
                    await res
            except Exception as e:
                logger.warning(f"Error sending log to WebSocket client: {e}")
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


async def run_publishing_pipeline(request: PublishRequest):
    """
    Sequentially processes enabled platforms using a single persistent Playwright browser context.
    If any platform fails, logs the error and continues to the next platform.
    Ensures browser context is properly closed.
    """
    enabled_platforms = [
        (plat, config)
        for plat, config in request.platforms.items()
        if config.enabled
    ]

    if not enabled_platforms:
        logger.info("No platforms enabled in publish request.")
        return

    await manager.broadcast_log(
        platform="system",
        status="info",
        message=f"Starting sequential publishing pipeline for {len(enabled_platforms)} platforms...",
    )

    async with async_playwright() as pw:
        context = await pw.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE_DIR),
            headless=HEADLESS,
            viewport={"width": 1280, "height": 800},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )

        try:
            for platform_name, config in enabled_platforms:
                await manager.broadcast_log(
                    platform=platform_name,
                    status="info",
                    message=f"Starting upload for {platform_name}...",
                )

                page = await context.new_page()

                # Build metadata dictionary from PlatformConfig
                metadata = config.model_dump()

                def log_callback(msg: str, stat: str = "info"):
                    # Helper callback for uploader instances to send log events
                    # We schedule broadcast in current event loop
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(
                            manager.broadcast_log(
                                platform=platform_name,
                                status=stat,
                                message=msg,
                            )
                        )
                    except RuntimeError:
                        pass

                try:
                    uploader = get_uploader(platform_name)
                    success = await uploader.upload(
                        page=page,
                        video_path=request.video_path,
                        metadata=metadata,
                        log_callback=log_callback,
                    )

                    if success:
                        await manager.broadcast_log(
                            platform=platform_name,
                            status="success",
                            message=f"Successfully uploaded to {platform_name}!",
                        )
                    else:
                        await manager.broadcast_log(
                            platform=platform_name,
                            status="error",
                            message=f"Upload to {platform_name} finished with failure or timeout.",
                        )
                except Exception as err:
                    logger.exception(f"Error publishing to {platform_name}: {err}")
                    await manager.broadcast_log(
                        platform=platform_name,
                        status="error",
                        message=f"Error publishing to {platform_name}: {str(err)}",
                    )
                finally:
                    try:
                        await page.close()
                    except Exception:
                        pass

        finally:
            await context.close()
            await manager.broadcast_log(
                platform="system",
                status="info",
                message="Publishing pipeline completed.",
            )
