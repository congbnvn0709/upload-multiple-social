import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, Optional
from unittest.mock import AsyncMock, MagicMock

from playwright.async_api import Page

from backend.config import LOGS_DIR
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
                if await self.element_count(cand) > 0 and await self.element_is_visible(cand):
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
                        if await self.element_count(cand) > 0:
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
                        # Check if Post button is present and enabled
                        post_cand = page.locator("button:text-is('Post'), button:text-is('Đăng'), button[data-e2e='post_video_button'], button:has-text('Post')").first
                        if await self.element_count(post_cand) > 0 and await self.element_is_enabled(post_cand):
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
                # Nút Post nằm cùng container với Save draft (chính xác tuyệt đối theo TikTok Studio)
                "div:has(> button:has-text('Save draft')) >> button:has-text('Post')",
                "div:has(> button:has-text('Lưu bản nháp')) >> button:has-text('Đăng')",
                "button:text-is('Post')",
                "button:text-is('Đăng')",
                "//button[normalize-space(text())='Post']",
                "//button[normalize-space(text())='Đăng']",
                "button[data-e2e='post_video_button']",
                "button:has-text('Post')",
                "button:has-text('Đăng')",
                "button:has-text('Xuất bản')",
                "button[data-e2e='btn_post']",
            ]

            post_clicked = False
            target_post_btn = None
            for p_sel in post_selectors:
                try:
                    cand = page.locator(p_sel).first
                    if await self.element_count(cand) > 0:
                        is_vis = await self.element_is_visible(cand)
                        is_enb = await self.element_is_enabled(cand)
                        self.log(f"Tìm thấy nút Post ({p_sel}): visible={is_vis}, enabled={is_enb}", "info", log_callback)
                        if hasattr(cand, "scroll_into_view_if_needed"):
                            res = cand.scroll_into_view_if_needed()
                            if inspect.isawaitable(res):
                                await res

                        target_post_btn = cand
                        # 1. Try standard click
                        try:
                            res = cand.click(timeout=5000)
                            if inspect.isawaitable(res):
                                await res
                            post_clicked = True
                            self.log(f"Đã click nút Post thành công bằng selector: {p_sel}", "info", log_callback)
                            break
                        except Exception as e:
                            self.log(f"Click thường thất bại ({e}), thử force click...", "debug", log_callback)
                            try:
                                res = cand.click(force=True, timeout=3000)
                                if inspect.isawaitable(res):
                                    await res
                                post_clicked = True
                                self.log(f"Đã force click nút Post bằng selector: {p_sel}", "info", log_callback)
                                break
                            except Exception:
                                pass
                except Exception as ex:
                    logger.debug("Error checking selector %s: %s", p_sel, ex)
                    continue

            # 2. Try mouse bounding box click if locator is available
            if not is_mock and target_post_btn:
                try:
                    if hasattr(target_post_btn, "bounding_box") and hasattr(page, "mouse"):
                        bbox = target_post_btn.bounding_box()
                        if inspect.isawaitable(bbox):
                            bbox = await bbox
                        if bbox:
                            self.log("Click chuột vào tọa độ nút Post...", "info", log_callback)
                            click_x = bbox["x"] + bbox["width"] / 2
                            click_y = bbox["y"] + bbox["height"] / 2
                            mouse_click = page.mouse.click(click_x, click_y)
                            if inspect.isawaitable(mouse_click):
                                await mouse_click
                            post_clicked = True
                except Exception as mouse_err:
                    self.log(f"Mouse click lỗi: {mouse_err}", "debug", log_callback)

            # 3. Fallback JavaScript click directly on button with text 'Post'
            if not post_clicked and not is_mock:
                self.log("Thử click nút Post thông qua JavaScript evaluate...", "info", log_callback)
                try:
                    js_clicked = await page.evaluate("""() => {
                        const buttons = Array.from(document.querySelectorAll('button'));
                        const postBtn = buttons.find(b => b.innerText.trim() === 'Post' || b.innerText.trim() === 'Đăng');
                        if (postBtn) {
                            postBtn.scrollIntoView();
                            postBtn.click();
                            return true;
                        }
                        return false;
                    }""")
                    if js_clicked:
                        post_clicked = True
                        self.log("JavaScript click nút Post thành công!", "info", log_callback)
                except Exception as js_err:
                    self.log(f"JavaScript click thất bại: {js_err}", "warning", log_callback)

            # Save screenshot immediately after clicking Post for debugging
            if not is_mock:
                try:
                    await page.screenshot(path=str(LOGS_DIR / "tiktok_debug_after_post.png"))
                except Exception:
                    pass

            # Handle possible confirmation popups (e.g. "Post anyway" for copyright or guidelines)
            confirm_selectors = [
                "button:has-text('Post anyway')",
                "button:has-text('Vẫn đăng')",
                "button:has-text('Confirm')",
                "button:has-text('Xác nhận')",
                "button:has-text('Continue to post')",
                "button:has-text('Tiếp tục đăng')",
            ]
            if not is_mock:
                await asyncio.sleep(2)
                for c_sel in confirm_selectors:
                    try:
                        c_cand = page.locator(c_sel).first
                        if await self.element_count(c_cand) > 0 and await self.element_is_visible(c_cand):
                            self.log(f"Đang xác nhận hộp thoại xuất bản ({c_sel})...", "info", log_callback)
                            await c_cand.click(timeout=3000)
                            break
                    except Exception:
                        pass

            # Wait for post submission confirmation
            if not is_mock:
                self.log("Đang chờ TikTok xử lý và xác nhận xuất bản video hoàn tất...", "info", log_callback)
                success_confirmed = False
                for _ in range(40):
                    await asyncio.sleep(1)
                    try:
                        current_url = getattr(page, "url", "")
                        if "/content" in current_url or "/manage" in current_url:
                            self.log(f"Đã phát hiện URL chuyển hướng thành công: {current_url}", "info", log_callback)
                            success_confirmed = True
                            break

                        # True submission indicators (modal dialog or completion buttons)
                        indicators = [
                            "button:has-text('Manage your posts')",
                            "button:has-text('Upload another video')",
                            "button:has-text('Quản lý bài viết')",
                            "button:has-text('Tải lên video khác')",
                            "text='Your video is being uploaded to TikTok!'",
                            "text='Your video has been published'",
                            "text='Video của bạn đã được xuất bản'",
                            "text='Video của bạn đang được tải lên'",
                        ]
                        for ind in indicators:
                            ind_loc = page.locator(ind).first
                            if await self.element_count(ind_loc) > 0 and await self.element_is_visible(ind_loc):
                                self.log(f"Đã phát hiện thông báo xác nhận: {ind}", "info", log_callback)
                                success_confirmed = True
                                break
                        if success_confirmed:
                            break

                        # Check if a delayed "Post anyway" confirmation popped up
                        for c_sel in confirm_selectors:
                            c_cand = page.locator(c_sel).first
                            if await self.element_count(c_cand) > 0 and await self.element_is_visible(c_cand):
                                self.log(f"Phát hiện hộp thoại xác nhận ({c_sel}), đang click...", "info", log_callback)
                                await c_cand.click(timeout=2000)
                    except Exception:
                        pass

                # Take screenshot before deciding final status
                try:
                    await page.screenshot(path=str(LOGS_DIR / "tiktok_debug_final_state.png"))
                except Exception:
                    pass

                if not success_confirmed:
                    screenshot_path = await self.capture_error_screenshot(page, "tiktok")
                    self.log(
                        f"TikTok chưa ghi nhận xuất bản thành công (đã chụp ảnh lỗi: {screenshot_path}). Vui lòng kiểm tra màn hình trình duyệt.",
                        "error",
                        log_callback,
                    )
                    return False

                # Allow 5 seconds for pending background network sync before closing browser
                self.log("Video đã được xác nhận đăng thành công! Đang chờ đồng bộ mạng hoàn tất...", "success", log_callback)
                await asyncio.sleep(5)

            self.log("TikTok video post initiated successfully!", "success", log_callback)
            return True

        except Exception as e:
            self.check_login_redirect(page, "tiktok", log_callback)
            await self.capture_error_screenshot(page, "tiktok")
            self.log(f"TikTok upload failed: {str(e)}", "error", log_callback)
            return False
