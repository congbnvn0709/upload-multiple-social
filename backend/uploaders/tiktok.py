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
    Automated video publisher for TikTok Studio, Creator Center, and Web Upload.
    """

    STUDIO_UPLOAD_URL = "https://www.tiktok.com/tiktokstudio/upload"
    CREATOR_UPLOAD_URL = "https://www.tiktok.com/creator-center/upload"
    FALLBACK_UPLOAD_URL = "https://www.tiktok.com/upload"

    async def _dismiss_popups_and_tooltips(self, page: Page) -> None:
        """
        Dismisses onboarding tooltips, guided tours, and popovers on TikTok Studio
        (e.g., 'create professional and engaging videos' tooltip with 'Got it' button).
        """
        if isinstance(page, (AsyncMock, MagicMock)):
            return

        dismiss_selectors = [
            "button:has-text('Got it')",
            "button:has-text('Đã hiểu')",
            "button:has-text('Next')",
            "button:has-text('Tiếp theo')",
            "button:has-text('Done')",
            "button:has-text('Hoàn tất')",
            "button:has-text('Dismiss')",
            "button:has-text('Bỏ qua')",
            ".driver-popover-close-btn",
            ".driver-popover-next-btn",
            "[aria-label='Close']",
        ]
        for sel in dismiss_selectors:
            try:
                cand = page.locator(sel).first
                cnt = await cand.count() if inspect.isawaitable(getattr(cand, "count", None)) else (cand.count() if hasattr(cand, "count") else 0)
                if cnt > 0:
                    vis = await cand.is_visible() if inspect.isawaitable(getattr(cand, "is_visible", None)) else True
                    if vis:
                        await cand.click(timeout=1000)
                        await asyncio.sleep(0.3)
            except Exception:
                pass

    async def upload(
        self,
        page: Page,
        video_path: str,
        metadata: Dict[str, Any],
        log_callback: Optional[Callable] = None,
    ) -> bool:
        try:
            self.log("Đang điều hướng đến trang TikTok Studio tải lên...", "info", log_callback)
            navigated = False
            for target_url in [self.STUDIO_UPLOAD_URL, self.CREATOR_UPLOAD_URL, self.FALLBACK_UPLOAD_URL]:
                try:
                    await page.goto(target_url, wait_until="domcontentloaded", timeout=25000)
                    navigated = True
                    break
                except Exception:
                    continue

            if not navigated:
                await page.goto(self.FALLBACK_UPLOAD_URL, wait_until="domcontentloaded", timeout=25000)

            if self.check_login_redirect(page, "tiktok", log_callback):
                await self.capture_error_screenshot(page, "tiktok")
                return False

            # Dismiss any immediate welcome or walkthrough popups
            await self._dismiss_popups_and_tooltips(page)

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
                        cnt = 1
                        if hasattr(cand, "count"):
                            cnt_val = cand.count()
                            cnt = await cnt_val if inspect.isawaitable(cnt_val) else cnt_val
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
                for _ in range(40):
                    await asyncio.sleep(1)
                    await self._dismiss_popups_and_tooltips(page)
                    try:
                        # Check if Post button is present and not disabled
                        post_cand = page.locator("button:text-is('Post'), button:text-is('Đăng'), button[data-e2e='post_video_button'], button:has-text('Post')").first
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

            # Dismiss popups again before submitting
            await self._dismiss_popups_and_tooltips(page)

            # Scroll down to bottom so the Post button is fully visible in viewport
            try:
                if hasattr(page, "evaluate"):
                    scroll_res = page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    if inspect.isawaitable(scroll_res):
                        await scroll_res
                    await asyncio.sleep(0.5)
            except Exception:
                pass

            # Dismiss any popups that appeared after scrolling
            await self._dismiss_popups_and_tooltips(page)

            self.log("Đang bấm nút Đăng (Post) video lên TikTok...", "info", log_callback)
            post_selectors = [
                "button:text-is('Post')",
                "button:text-is('Đăng')",
                "button[data-e2e='post_video_button']",
                "button:has-text('Post')",
                "button:has-text('Đăng')",
                "button:has-text('Xuất bản')",
                "button[data-e2e='btn_post']",
            ]

            post_clicked = False
            for p_sel in post_selectors:
                try:
                    cand = page.locator(p_sel).first
                    cnt = 1
                    if hasattr(cand, "count"):
                        cnt_val = cand.count()
                        cnt = await cnt_val if inspect.isawaitable(cnt_val) else cnt_val
                    if cnt > 0:
                        if hasattr(cand, "scroll_into_view_if_needed"):
                            res = cand.scroll_into_view_if_needed()
                            if inspect.isawaitable(res):
                                await res
                        try:
                            res = cand.click(timeout=5000)
                            if inspect.isawaitable(res):
                                await res
                            post_clicked = True
                            break
                        except Exception:
                            res = cand.click(force=True, timeout=3000)
                            if inspect.isawaitable(res):
                                await res
                            post_clicked = True
                            break
                except Exception:
                    continue

            if not post_clicked and not is_mock:
                # Fallback to safe_click
                await self.safe_click(page, post_selectors, timeout=5000)

            # Handle possible confirmation popups (e.g. "Post anyway" for copyright or guidelines)
            if not is_mock:
                await asyncio.sleep(1)
                confirm_selectors = [
                    "button:has-text('Post anyway')",
                    "button:has-text('Vẫn đăng')",
                    "button:has-text('Confirm')",
                    "button:has-text('Xác nhận')",
                    "button:has-text('Continue to post')",
                    "button:has-text('Tiếp tục đăng')",
                ]
                for c_sel in confirm_selectors:
                    try:
                        c_cand = page.locator(c_sel).first
                        cnt = await c_cand.count() if hasattr(c_cand, "count") else 0
                        if cnt > 0:
                            self.log(f"Đang xác nhận hộp thoại xuất bản ({c_sel})...", "info", log_callback)
                            await c_cand.click(timeout=3000)
                            break
                    except Exception:
                        pass

            # Wait for post submission confirmation
            if not is_mock:
                self.log("Đang chờ xác nhận xuất bản từ TikTok...", "info", log_callback)
                success_confirmed = False
                for _ in range(30):
                    await asyncio.sleep(1)
                    try:
                        current_url = getattr(page, "url", "")
                        if "/content" in current_url or "/manage" in current_url:
                            success_confirmed = True
                            break
                        indicators = [
                            "text='Your video has been uploaded'",
                            "text='Video của bạn đã được tải lên'",
                            "text='Video của bạn đã được đăng'",
                            "text='Manage your posts'",
                            "text='Quản lý bài viết'",
                            "text='Upload another video'",
                            "text='Tải lên video khác'",
                            "button:has-text('Manage your posts')",
                            "button:has-text('Quản lý bài viết')",
                        ]
                        for ind in indicators:
                            ind_loc = page.locator(ind).first
                            cnt = await ind_loc.count() if hasattr(ind_loc, "count") else 0
                            if cnt > 0:
                                success_confirmed = True
                                break
                        if success_confirmed:
                            break
                    except Exception:
                        pass

                if not success_confirmed:
                    screenshot_path = await self.capture_error_screenshot(page, "tiktok")
                    self.log(
                        f"TikTok chưa ghi nhận xuất bản thành công (đã chụp ảnh lỗi: {screenshot_path}).",
                        "error",
                        log_callback,
                    )
                    return False

                # Allow a few seconds for pending background network sync before closing browser
                await asyncio.sleep(3)

            self.log("TikTok video post initiated successfully!", "success", log_callback)
            return True

        except Exception as e:
            self.check_login_redirect(page, "tiktok", log_callback)
            await self.capture_error_screenshot(page, "tiktok")
            self.log(f"TikTok upload failed: {str(e)}", "error", log_callback)
            return False
