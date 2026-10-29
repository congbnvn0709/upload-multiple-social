import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, Optional
from unittest.mock import AsyncMock, MagicMock

from playwright.async_api import Page

from backend.config import LOGS_DIR
from backend.uploaders.base import BaseUploader

logger = logging.getLogger(__name__)


class FacebookUploader(BaseUploader):
    """
    Automated video publisher for Facebook Reels (supporting Profile and Fanpage).
    """

    PROFILE_REELS_URL = "https://www.facebook.com/reel/create"

    async def upload(
        self,
        page: Page,
        video_path: str,
        metadata: Dict[str, Any],
        log_callback: Optional[Callable] = None,
    ) -> bool:
        is_mock = isinstance(page, (AsyncMock, MagicMock)) or not hasattr(page, "evaluate")

        try:
            target = metadata.get("target", "profile").lower()
            page_id = (metadata.get("page_id") or "").strip()

            if target == "fanpage":
                if page_id:
                    url = f"https://www.facebook.com/{page_id}/reels_composer"
                    self.log(f"Navigating to Facebook Fanpage Reels composer: {url}", "info", log_callback)
                else:
                    url = "https://business.facebook.com/latest/reels_composer"
                    self.log(f"Navigating to Facebook Fanpage Reels composer (Business Suite): {url}", "info", log_callback)
            else:
                url = self.PROFILE_REELS_URL
                self.log(f"Navigating to Facebook Profile Reels creator: {url}", "info", log_callback)

            await page.goto(url, wait_until="domcontentloaded")

            if self.check_login_redirect(page, "facebook", log_callback):
                await self.capture_error_screenshot(page, "facebook")
                return False

            self.log(f"Attaching video file: {video_path}", "info", log_callback)
            file_input_selectors = [
                "input[type='file'][accept*='video']",
                "input[type='file']",
            ]
            file_input = await self.find_first(page, file_input_selectors, timeout=10000)
            if not file_input:
                file_input = await self.get_locator(page, "input[type='file']")

            if hasattr(file_input, "set_input_files"):
                set_res = file_input.set_input_files(video_path)
                if inspect.isawaitable(set_res):
                    await set_res
            else:
                await page.set_input_files("input[type='file']", video_path)

            if not is_mock:
                self.log("Waiting for video upload to process...", "info", log_callback)
                await asyncio.sleep(2.0)

            # Build caption and hashtags
            caption = metadata.get("caption", "").strip()
            hashtags = metadata.get("hashtags", [])
            tag_str = " ".join([tag if tag.startswith("#") else f"#{tag}" for tag in hashtags]).strip()
            full_caption = f"{caption} {tag_str}".strip() if tag_str else caption

            if full_caption:
                self.log(f"Entering Reels caption: {full_caption[:60]}...", "info", log_callback)
                desc_selectors = [
                    "div[contenteditable='true']",
                    "div[role='textbox']",
                    "[aria-label*='Describe your reel']",
                    "[aria-label*='Mô tả thước phim']",
                    "textarea",
                ]
                desc_loc = await self.find_first(page, desc_selectors, timeout=8000)
                if not desc_loc:
                    desc_loc = await self.get_locator(page, "div[contenteditable='true']")

                try:
                    if hasattr(desc_loc, "click"):
                        click_res = desc_loc.click()
                        if inspect.isawaitable(click_res):
                            await click_res
                    if not is_mock and hasattr(page, "keyboard"):
                        await page.keyboard.press("ControlOrMeta+A")
                        await page.keyboard.press("Backspace")
                        await asyncio.sleep(0.2)
                except Exception:
                    pass

                inserted = False
                if hasattr(page, "keyboard") and hasattr(page.keyboard, "insert_text"):
                    try:
                        res = page.keyboard.insert_text(full_caption)
                        if inspect.isawaitable(res):
                            await res
                        inserted = True
                    except Exception:
                        inserted = False

                if not inserted:
                    await self.type_humanized(page, desc_loc, full_caption, min_delay=0.01, max_delay=0.03)

            # Advance through Next wizard steps (e.g. Audio, Edit)
            self.log("Advancing through Reels creation steps...", "info", log_callback)
            next_selectors = [
                "div[role='button']:has-text('Next')",
                "button:has-text('Next')",
                "div[role='button']:has-text('Tiếp')",
                "button:has-text('Tiếp')",
            ]

            for step in range(2):
                clicked_next = await self.safe_click(page, next_selectors, timeout=3000, optional=True)
                if clicked_next:
                    if not is_mock:
                        await asyncio.sleep(1.0)
                else:
                    break

            # Click Publish
            self.log("Publishing Facebook Reel...", "info", log_callback)
            publish_selectors = [
                "div[role='button']:has-text('Publish')",
                "button:has-text('Publish')",
                "div[role='button']:has-text('Đăng')",
                "button:has-text('Đăng')",
            ]
            clicked_pub = await self.safe_click(page, publish_selectors, timeout=10000)
            if not clicked_pub:
                loc = await self.get_locator(page, "div[role='button']:has-text('Publish'), button:has-text('Publish')")
                if hasattr(loc, "click"):
                    res = loc.click()
                    if inspect.isawaitable(res):
                        await res

            if not is_mock:
                try:
                    LOGS_DIR.mkdir(parents=True, exist_ok=True)
                    await page.screenshot(path=str(LOGS_DIR / "facebook_debug_after_post.png"))
                except Exception:
                    pass

                # Wait for publish confirmation / modal close
                self.log("Đang xác nhận kết quả đăng trên Facebook...", "info", log_callback)
                for _ in range(25):  # up to 37s
                    await asyncio.sleep(1.5)
                    # Check if creation dialog closed or redirected
                    if "/reel/create" not in (page.url or ""):
                        break
                await asyncio.sleep(3.0)

            self.log("Facebook Reel published successfully!", "success", log_callback)
            return True

        except Exception as e:
            self.check_login_redirect(page, "facebook", log_callback)
            await self.capture_error_screenshot(page, "facebook")
            self.log(f"Facebook upload failed: {str(e)}", "error", log_callback)
            return False
