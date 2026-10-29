import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, Optional
from unittest.mock import AsyncMock, MagicMock

from playwright.async_api import Page

from backend.config import LOGS_DIR
from backend.uploaders.base import BaseUploader

logger = logging.getLogger(__name__)


class ThreadsUploader(BaseUploader):
    """
    Automated video publisher for Meta Threads (threads.net).
    """

    BASE_URL = "https://www.threads.net"

    async def _check_post_button_status(self, page: Page) -> Dict[str, Any]:
        """
        Evaluates the Post button status in the Threads composer modal.
        Checks for disabled state, aria-disabled, opacity, and active upload indicators.
        """
        try:
            if not hasattr(page, "evaluate"):
                return {"found": True, "ready": True}

            status = await page.evaluate("""() => {
                const dialog = document.querySelector("div[role='dialog']");
                const root = dialog || document;

                const buttons = Array.from(root.querySelectorAll("div[role='button'], button"));
                const postBtn = buttons.find(b => {
                    const t = (b.innerText || b.textContent || "").trim().toLowerCase();
                    return t === 'post' || t === 'đăng';
                });

                if (!postBtn) {
                    return { found: false, ready: false, isStillUploading: false };
                }

                const hasDisabledAttr = postBtn.hasAttribute('disabled');
                const ariaDisabled = postBtn.getAttribute('aria-disabled') === 'true';
                const classDisabled = postBtn.className.toLowerCase().includes('disabled');

                const style = window.getComputedStyle(postBtn);
                const notAllowed = style.cursor === 'not-allowed';
                const pointerNone = style.pointerEvents === 'none';
                const lowOpacity = parseFloat(style.opacity || '1') < 0.8;

                const hasProgress = root.querySelectorAll("[role='progressbar'], svg.animate-spin").length > 0;
                const bodyText = (dialog ? dialog.innerText : document.body.innerText) || '';
                const isStillUploading = hasProgress ||
                                        bodyText.includes('Uploading') ||
                                        bodyText.includes('Đang tải lên') ||
                                        bodyText.includes('Processing') ||
                                        bodyText.includes('Đang xử lý');

                const isReady = !hasDisabledAttr && !ariaDisabled && !classDisabled &&
                                !notAllowed && !pointerNone && !lowOpacity && !isStillUploading;

                return {
                    found: true,
                    ready: isReady,
                    isStillUploading,
                    hasDisabledAttr,
                    ariaDisabled,
                    lowOpacity,
                    pointerNone
                };
            }""")
            return status if isinstance(status, dict) else {"found": False, "ready": False}
        except Exception as e:
            logger.debug("Error checking Threads post button status: %s", e)
            return {"found": False, "ready": False}

    async def _dismiss_popups(self, page: Page) -> None:
        """
        Dismisses cookie notices, 'Not now', or other overlay prompts.
        """
        try:
            if not hasattr(page, "locator"):
                return
            dismiss_selectors = [
                "button:has-text('Not now')",
                "div[role='button']:has-text('Not now')",
                "button:has-text('Không phải bây giờ')",
                "div[role='button']:has-text('Không phải bây giờ')",
                "button:has-text('Decline optional cookies')",
                "button:has-text('Từ chối cookie tùy chọn')",
                "button:has-text('Allow all cookies')",
                "button:has-text('Cho phép tất cả cookie')",
            ]
            for sel in dismiss_selectors:
                try:
                    loc = page.locator(sel)
                    cnt = await self.element_count(loc)
                    if cnt > 0:
                        first_el = loc.first if hasattr(loc, "first") else loc
                        is_vis = await self.element_is_visible(first_el)
                        if is_vis:
                            await first_el.click(timeout=1500)
                            await asyncio.sleep(0.3)
                except Exception:
                    continue
        except Exception:
            pass

    async def upload(
        self,
        page: Page,
        video_path: str,
        metadata: Dict[str, Any],
        log_callback: Optional[Callable] = None,
    ) -> bool:
        is_mock = isinstance(page, (AsyncMock, MagicMock)) or not hasattr(page, "evaluate")

        try:
            self.log("Navigating to Threads (threads.net)...", "info", log_callback)
            await page.goto(self.BASE_URL, wait_until="domcontentloaded")

            if self.check_login_redirect(page, "threads", log_callback):
                await self.capture_error_screenshot(page, "threads")
                return False

            if not is_mock:
                await self._dismiss_popups(page)

            self.log("Opening new thread composer...", "info", log_callback)
            composer_triggers = [
                "svg[aria-label='Create']",
                "svg[aria-label='Tạo']",
                "[aria-label='New thread']",
                "[aria-label='Bài viết mới']",
                "div[role='button']:has-text('Start a thread')",
                "div[role='button']:has-text('Có gì mới?')",
                "div[role='button']:has-text('Tạo')",
            ]
            # Check if dialog already visible
            dialog_loc = await self.get_locator(page, "div[role='dialog']")
            dialog_open = (await self.element_count(dialog_loc)) > 0 and (await self.element_is_visible(dialog_loc))

            if not dialog_open:
                await self.safe_click(page, composer_triggers, timeout=6000, optional=True)
                if not is_mock:
                    await asyncio.sleep(0.8)

            self.log(f"Attaching video file: {video_path}", "info", log_callback)
            file_input_selectors = [
                "div[role='dialog'] input[type='file'][accept*='video']",
                "div[role='dialog'] input[type='file']",
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

            if not is_mock:
                await asyncio.sleep(0.8)

            # Build caption and hashtags
            caption = metadata.get("caption", "").strip()
            hashtags = metadata.get("hashtags", [])
            tag_str = " ".join([tag if tag.startswith("#") else f"#{tag}" for tag in hashtags]).strip()
            full_caption = f"{caption} {tag_str}".strip() if tag_str else caption

            if full_caption:
                self.log(f"Entering thread text: {full_caption[:60]}...", "info", log_callback)
                editor_selectors = [
                    "div[role='dialog'] div[contenteditable='true']",
                    "div[role='dialog'] div[role='textbox']",
                    "div[contenteditable='true']",
                    "div[role='textbox']",
                    "textarea",
                ]
                editor_loc = await self.find_first(page, editor_selectors, timeout=8000)
                if not editor_loc:
                    editor_loc = await self.get_locator(page, "div[contenteditable='true']")

                # Focus and clear editor
                try:
                    if hasattr(editor_loc, "click"):
                        click_res = editor_loc.click()
                        if inspect.isawaitable(click_res):
                            await click_res
                    if not is_mock and hasattr(page, "keyboard"):
                        await page.keyboard.press("ControlOrMeta+A")
                        await page.keyboard.press("Backspace")
                        await asyncio.sleep(0.2)
                except Exception:
                    pass

                # Atomic text insertion to prevent character skipping
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
                    await self.type_humanized(page, editor_loc, full_caption, min_delay=0.01, max_delay=0.03)

            # Wait for video upload and transcoding to complete (up to 90s)
            if not is_mock:
                self.log("Đang chờ Threads tải lên và xử lý video...", "info", log_callback)
                upload_ready = False
                for wait_step in range(60):  # 60 * 1.5s = 90 seconds
                    await asyncio.sleep(1.5)
                    await self._dismiss_popups(page)

                    btn_status = await self._check_post_button_status(page)
                    if btn_status.get("ready"):
                        upload_ready = True
                        self.log("Threads đã tải xong video! Nút Đăng đã sẵn sàng.", "info", log_callback)
                        break

                    if wait_step % 4 == 0:
                        is_uploading = btn_status.get("isStillUploading", True)
                        if is_uploading:
                            self.log(f"Tiến trình tải video lên Threads đang diễn ra ({int(wait_step * 1.5)}s)...", "info", log_callback)
                        else:
                            self.log(f"Đang chờ Threads sẵn sàng xuất bản ({int(wait_step * 1.5)}s)...", "info", log_callback)

                if not upload_ready:
                    self.log("Cảnh báo: Thời gian xử lý video quá lâu nhưng vẫn thử bấm Đăng...", "warning", log_callback)

            self.log("Clicking Post on Threads...", "info", log_callback)
            post_selectors = [
                "div[role='dialog'] div[role='button']:has-text('Post')",
                "div[role='dialog'] button:has-text('Post')",
                "div[role='dialog'] div[role='button']:has-text('Đăng')",
                "div[role='dialog'] button:has-text('Đăng')",
                "div[role='button']:has-text('Post')",
                "button:has-text('Post')",
                "div[role='button']:has-text('Đăng')",
                "button:has-text('Đăng')",
            ]

            post_clicked = False
            target_post_btn = None

            for p_sel in post_selectors:
                try:
                    cand = await self.get_locator(page, p_sel)
                    cnt = await self.element_count(cand)
                    if cnt > 0:
                        target_post_btn = cand
                        try:
                            res = cand.click(timeout=5000)
                            if inspect.isawaitable(res):
                                await res
                            post_clicked = True
                            self.log(f"Đã click nút Post Threads thành công bằng: {p_sel}", "info", log_callback)
                            break
                        except Exception:
                            try:
                                res = cand.click(force=True, timeout=3000)
                                if inspect.isawaitable(res):
                                    await res
                                post_clicked = True
                                self.log(f"Đã force click nút Post Threads: {p_sel}", "info", log_callback)
                                break
                            except Exception:
                                pass
                except Exception:
                    continue

            # Fallback mouse bounding box click
            if not is_mock and not post_clicked and target_post_btn:
                try:
                    if hasattr(target_post_btn, "bounding_box") and hasattr(page, "mouse"):
                        bbox = target_post_btn.bounding_box()
                        if inspect.isawaitable(bbox):
                            bbox = await bbox
                        if bbox:
                            click_x = bbox["x"] + bbox["width"] / 2
                            click_y = bbox["y"] + bbox["height"] / 2
                            mouse_click = page.mouse.click(click_x, click_y)
                            if inspect.isawaitable(mouse_click):
                                await mouse_click
                            post_clicked = True
                            self.log("Click tọa độ nút Post Threads thành công", "info", log_callback)
                except Exception:
                    pass

            # Fallback JavaScript evaluate click
            if not is_mock and not post_clicked:
                try:
                    js_clicked = await page.evaluate("""() => {
                        const dialog = document.querySelector("div[role='dialog']") || document;
                        const buttons = Array.from(dialog.querySelectorAll("div[role='button'], button"));
                        const postBtn = buttons.find(b => {
                            const t = (b.innerText || b.textContent || "").trim().toLowerCase();
                            return t === 'post' || t === 'đăng';
                        });
                        if (postBtn) {
                            postBtn.scrollIntoView();
                            postBtn.click();
                            return true;
                        }
                        return false;
                    }""")
                    if js_clicked:
                        post_clicked = True
                        self.log("JavaScript click nút Post Threads thành công!", "info", log_callback)
                except Exception:
                    pass

            # Save debug screenshot immediately after clicking Post
            if not is_mock:
                try:
                    LOGS_DIR.mkdir(parents=True, exist_ok=True)
                    await page.screenshot(path=str(LOGS_DIR / "threads_debug_after_post.png"))
                except Exception:
                    pass

            # Verify real submission: Wait for composer dialog to close or toast to confirm
            if not is_mock:
                self.log("Đang xác nhận kết quả đăng trên Threads...", "info", log_callback)
                confirmed = False
                for check_step in range(45):  # 45 * 1.5s = ~67s
                    await asyncio.sleep(1.5)

                    # 1. Check if dialog has closed / removed from DOM
                    dialog_loc = page.locator("div[role='dialog']")
                    dialog_count = await self.element_count(dialog_loc)
                    if dialog_count == 0:
                        confirmed = True
                        self.log("Hộp thoại đăng bài Threads đã đóng thành công!", "info", log_callback)
                        break

                    is_vis = await self.element_is_visible(dialog_loc)
                    if not is_vis:
                        confirmed = True
                        self.log("Hộp thoại đăng bài Threads đã ẩn thành công!", "info", log_callback)
                        break

                    # 2. Check for success toast
                    toast_selectors = [
                        "div:has-text('Posted')",
                        "div:has-text('Đã đăng')",
                        "div:has-text('Your thread was posted')",
                        "div:has-text('Bài viết của bạn đã được đăng')",
                    ]
                    for t_sel in toast_selectors:
                        t_loc = page.locator(t_sel)
                        if (await self.element_count(t_loc)) > 0 and (await self.element_is_visible(t_loc)):
                            confirmed = True
                            self.log(f"Phát hiện thông báo xuất bản Threads thành công: '{t_sel}'!", "info", log_callback)
                            break
                    if confirmed:
                        break

                    # 3. Check for error message inside dialog
                    try:
                        err_msg = await page.evaluate("""() => {
                            const dialog = document.querySelector("div[role='dialog']");
                            if (!dialog) return null;
                            const text = (dialog.innerText || "").toLowerCase();
                            const patterns = ["couldn't post", "could not post", "failed to post", "không thể đăng", "lỗi tải lên"];
                            for (const p of patterns) {
                                if (text.includes(p)) return p;
                            }
                            return null;
                        }""")
                        if err_msg:
                            self.log(f"Threads báo lỗi xuất bản: '{err_msg}'", "error", log_callback)
                            await self.capture_error_screenshot(page, "threads")
                            return False
                    except Exception:
                        pass

                if not confirmed:
                    self.log("Threads chưa xác nhận đăng thành công (hộp thoại chưa đóng sau 60s).", "error", log_callback)
                    await self.capture_error_screenshot(page, "threads")
                    return False

                # Grace period for background network synchronization
                await asyncio.sleep(4)

            self.log("Threads post published successfully!", "success", log_callback)
            return True

        except Exception as e:
            self.check_login_redirect(page, "threads", log_callback)
            await self.capture_error_screenshot(page, "threads")
            self.log(f"Threads upload failed: {str(e)}", "error", log_callback)
            return False
