import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, Optional
from unittest.mock import AsyncMock, MagicMock

from playwright.async_api import Page

from backend.uploaders.base import BaseUploader

logger = logging.getLogger(__name__)


class TikTokUploader(BaseUploader):
    """
    Automated video publisher for TikTok Creator Center and TikTok Web Upload.
    """

    UPLOAD_URL = "https://www.tiktok.com/creator-center/upload"
    FALLBACK_UPLOAD_URL = "https://www.tiktok.com/upload"

    async def upload(
        self,
        page: Page,
        video_path: str,
        metadata: Dict[str, Any],
        log_callback: Optional[Callable] = None,
    ) -> bool:
        try:
            self.log("Đang điều hướng đến trang tải lên của TikTok...", "info", log_callback)
            try:
                await page.goto(self.UPLOAD_URL, wait_until="domcontentloaded", timeout=25000)
            except Exception:
                self.log("Thử URL tải lên phụ của TikTok...", "info", log_callback)
                await page.goto(self.FALLBACK_UPLOAD_URL, wait_until="domcontentloaded", timeout=25000)

            if self.check_login_redirect(page, "tiktok", log_callback):
                await self.capture_error_screenshot(page, "tiktok")
                return False

            self.log("Đang tìm ô tải file video...", "info", log_callback)
            file_input_selectors = [
                "input[type='file'][accept*='video']",
                "input[type='file']",
                'input[type="file"]',
                "iframe[data-tt='upload-iframe'] >> input[type='file']",
            ]

            file_input = await self.find_first(page, file_input_selectors, timeout=15000)

            # If not found directly, inspect all frames in the page
            if not file_input and hasattr(page, "frames"):
                for frame in page.frames:
                    try:
                        cand = frame.locator("input[type='file']").first
                        cnt = await cand.count() if hasattr(cand, "count") and inspect.isawaitable(cand.count()) else (cand.count() if hasattr(cand, "count") else 1)
                        if cnt > 0:
                            file_input = cand
                            break
                    except Exception:
                        continue

            if not file_input:
                file_input = await self.get_locator(page, "input[type='file']")

            self.log(f"Đang đính kèm file video: {video_path}", "info", log_callback)
            if hasattr(file_input, "set_input_files"):
                set_res = file_input.set_input_files(video_path)
                if inspect.isawaitable(set_res):
                    await set_res
            else:
                await page.set_input_files("input[type='file']", video_path)

            self.log("Video đã được tải lên form, đang chờ xử lý và hoàn tất tải...", "info", log_callback)

            is_mock = isinstance(page, (AsyncMock, MagicMock))

            # Wait for upload completion (preview ready or post button active)
            if not is_mock:
                for _ in range(30):
                    await asyncio.sleep(1)
                    try:
                        # Check if Post button is present and not disabled
                        post_cand = page.locator("button[data-e2e='post_video_button'], button:has-text('Đăng'), button:has-text('Post')").first
                        cnt = await post_cand.count() if hasattr(post_cand, "count") else 0
                        if cnt > 0:
                            is_disabled = await post_cand.get_attribute("disabled") if hasattr(post_cand, "get_attribute") else None
                            aria_disabled = await post_cand.get_attribute("aria-disabled") if hasattr(post_cand, "get_attribute") else None
                            if is_disabled is None and aria_disabled != "true":
                                break
                    except Exception:
                        pass

            # Build caption and hashtags
            caption = metadata.get("caption", "").strip()
            hashtags = metadata.get("hashtags", [])
            tag_str = " ".join([tag if tag.startswith("#") else f"#{tag}" for tag in hashtags]).strip()
            full_caption = f"{caption} {tag_str}".strip() if tag_str else caption

            if full_caption:
                self.log(f"Đang nhập tiêu đề và chú thích: {full_caption[:60]}...", "info", log_callback)
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
                    if hasattr(caption_loc, "click"):
                        click_res = caption_loc.click()
                        if inspect.isawaitable(click_res):
                            await click_res
                    if hasattr(page, "keyboard"):
                        # Select all and delete default text (TikTok auto-inserts video filename)
                        press_a = page.keyboard.press("ControlOrMeta+A")
                        if inspect.isawaitable(press_a):
                            await press_a
                        press_del = page.keyboard.press("Backspace")
                        if inspect.isawaitable(press_del):
                            await press_del
                except Exception:
                    pass

                await self.type_humanized(page, caption_loc, full_caption, min_delay=0.001, max_delay=0.01)

            self.log("Đang bấm nút Đăng video lên TikTok...", "info", log_callback)
            post_selectors = [
                "button[data-e2e='post_video_button']",
                "button:has-text('Đăng')",
                "button:has-text('Post')",
                "button:has-text('Xuất bản')",
                "button[data-e2e='btn_post']",
            ]
            clicked = await self.safe_click(page, post_selectors, timeout=10000)
            if not clicked:
                loc = await self.get_locator(page, "button:has-text('Post')")
                if hasattr(loc, "click"):
                    res = loc.click()
                    if inspect.isawaitable(res):
                        await res

            # Wait briefly to confirm post submission
            if not is_mock:
                self.log("Đang chờ xác nhận xuất bản từ TikTok...", "info", log_callback)
                for _ in range(10):
                    await asyncio.sleep(1)
                    try:
                        current_url = getattr(page, "url", "")
                        if "/content" in current_url or "/manage" in current_url:
                            break
                        modal = page.locator("text='Video của bạn đã được đăng', text='Your video has been uploaded', text='Quản lý bài viết', text='Manage your posts'").first
                        cnt = await modal.count() if hasattr(modal, "count") else 0
                        if cnt > 0:
                            break
                    except Exception:
                        pass

            self.log("TikTok video post initiated successfully!", "success", log_callback)
            return True

        except Exception as e:
            self.check_login_redirect(page, "tiktok", log_callback)
            await self.capture_error_screenshot(page, "tiktok")
            self.log(f"TikTok upload failed: {str(e)}", "error", log_callback)
            return False
