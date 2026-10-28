import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, Optional

from playwright.async_api import Page

from backend.uploaders.base import BaseUploader

logger = logging.getLogger(__name__)


class TikTokUploader(BaseUploader):
    """
    Automated video publisher for TikTok Creator Center.
    """

    UPLOAD_URL = "https://www.tiktok.com/creator-center/upload"

    async def upload(
        self,
        page: Page,
        video_path: str,
        metadata: Dict[str, Any],
        log_callback: Optional[Callable] = None,
    ) -> bool:
        try:
            self.log("Navigating to TikTok Creator Center upload page...", "info", log_callback)
            await page.goto(self.UPLOAD_URL, wait_until="domcontentloaded")

            self.log("Locating file input...", "info", log_callback)
            file_input_selectors = [
                "input[type='file']",
                'input[type="file"]',
                "iframe[data-tt='upload-iframe'] >> input[type='file']",
            ]

            file_input = await self.find_first(page, file_input_selectors, timeout=15000)
            if not file_input:
                file_input = await self.get_locator(page, "input[type='file']")

            self.log(f"Attaching video file: {video_path}", "info", log_callback)
            if hasattr(file_input, "set_input_files"):
                set_res = file_input.set_input_files(video_path)
                if inspect.isawaitable(set_res):
                    await set_res
            else:
                await page.set_input_files("input[type='file']", video_path)

            self.log("Video uploaded to form. Waiting for processing...", "info", log_callback)
            await asyncio.sleep(0.5)

            # Build caption and hashtags
            caption = metadata.get("caption", "").strip()
            hashtags = metadata.get("hashtags", [])
            tag_str = " ".join([tag if tag.startswith("#") else f"#{tag}" for tag in hashtags]).strip()
            full_caption = f"{caption} {tag_str}".strip() if tag_str else caption

            if full_caption:
                self.log(f"Entering caption: {full_caption[:60]}...", "info", log_callback)
                caption_selectors = [
                    "div.public-DraftEditor-content",
                    "div[contenteditable='true']",
                    "[aria-label*='Description']",
                    "[aria-label*='Chú thích']",
                    "div[data-e2e='caption_editor']",
                ]
                caption_loc = await self.find_first(page, caption_selectors, timeout=10000)
                if not caption_loc:
                    caption_loc = await self.get_locator(page, "div.public-DraftEditor-content")

                try:
                    click_res = caption_loc.click()
                    if inspect.isawaitable(click_res):
                        await click_res
                    press_a = page.keyboard.press("Meta+A")
                    if inspect.isawaitable(press_a):
                        await press_a
                    press_del = page.keyboard.press("Backspace")
                    if inspect.isawaitable(press_del):
                        await press_del
                except Exception:
                    pass

                await self.type_humanized(page, caption_loc, full_caption, min_delay=0.001, max_delay=0.01)

            self.log("Submitting video (clicking Post)...", "info", log_callback)
            post_selectors = [
                "button[data-e2e='post_video_button']",
                "button:has-text('Post')",
                "button:has-text('Đăng')",
                "button[data-e2e='btn_post']",
            ]
            clicked = await self.safe_click(page, post_selectors, timeout=10000)
            if not clicked:
                loc = await self.get_locator(page, "button:has-text('Post')")
                if hasattr(loc, "click"):
                    res = loc.click()
                    if inspect.isawaitable(res):
                        await res

            self.log("TikTok video post initiated successfully!", "success", log_callback)
            return True

        except Exception as e:
            self.log(f"TikTok upload failed: {str(e)}", "error", log_callback)
            return False
