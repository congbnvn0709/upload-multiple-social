import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, Optional

from playwright.async_api import Page

from backend.uploaders.base import BaseUploader

logger = logging.getLogger(__name__)


class ThreadsUploader(BaseUploader):
    """
    Automated video publisher for Meta Threads (threads.net).
    """

    BASE_URL = "https://www.threads.net"

    async def upload(
        self,
        page: Page,
        video_path: str,
        metadata: Dict[str, Any],
        log_callback: Optional[Callable] = None,
    ) -> bool:
        try:
            self.log("Navigating to Threads (threads.net)...", "info", log_callback)
            await page.goto(self.BASE_URL, wait_until="domcontentloaded")

            if self.check_login_redirect(page, "threads", log_callback):
                await self.capture_error_screenshot(page, "threads")
                return False

            self.log("Opening new thread composer...", "info", log_callback)
            composer_triggers = [
                "svg[aria-label='Create']",
                "svg[aria-label='Tạo']",
                "[aria-label='New thread']",
                "div[role='button']:has-text('Start a thread')",
                "div[role='button']:has-text('Có gì mới?')",
                "div[role='button']:has-text('Tạo')",
            ]
            await self.safe_click(page, composer_triggers, timeout=5000, optional=True)
            await asyncio.sleep(0.5)

            self.log(f"Attaching video file: {video_path}", "info", log_callback)
            file_input_selectors = [
                "input[type='file'][accept*='video']",
                "input[type='file']",
            ]
            file_input = await self.find_first(page, file_input_selectors, timeout=8000)
            if not file_input:
                file_input = await self.get_locator(page, "input[type='file']")

            if hasattr(file_input, "set_input_files"):
                set_res = file_input.set_input_files(video_path)
                if inspect.isawaitable(set_res):
                    await set_res
            else:
                await page.set_input_files("input[type='file']", video_path)

            self.log("Waiting for video preview to load...", "info", log_callback)
            await asyncio.sleep(0.5)

            # Build caption and hashtags
            caption = metadata.get("caption", "").strip()
            hashtags = metadata.get("hashtags", [])
            tag_str = " ".join([tag if tag.startswith("#") else f"#{tag}" for tag in hashtags]).strip()
            full_caption = f"{caption} {tag_str}".strip() if tag_str else caption

            if full_caption:
                self.log(f"Entering thread text: {full_caption[:60]}...", "info", log_callback)
                editor_selectors = [
                    "div[contenteditable='true']",
                    "div[role='textbox']",
                    "textarea",
                ]
                editor_loc = await self.find_first(page, editor_selectors, timeout=8000)
                if not editor_loc:
                    editor_loc = await self.get_locator(page, "div[contenteditable='true']")

                await self.type_humanized(page, editor_loc, full_caption, min_delay=0.001, max_delay=0.01)

            self.log("Clicking Post on Threads...", "info", log_callback)
            post_selectors = [
                "div[role='button']:has-text('Post')",
                "button:has-text('Post')",
                "div[role='button']:has-text('Đăng')",
                "button:has-text('Đăng')",
            ]
            clicked = await self.safe_click(page, post_selectors, timeout=10000)
            if not clicked:
                loc = await self.get_locator(page, "div[role='button']:has-text('Post'), button:has-text('Post')")
                if hasattr(loc, "click"):
                    res = loc.click()
                    if inspect.isawaitable(res):
                        await res

            self.log("Threads post published successfully!", "success", log_callback)
            return True

        except Exception as e:
            self.check_login_redirect(page, "threads", log_callback)
            await self.capture_error_screenshot(page, "threads")
            self.log(f"Threads upload failed: {str(e)}", "error", log_callback)
            return False
