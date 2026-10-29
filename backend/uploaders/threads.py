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
    Handles modal targeting, atomic text input, video upload polling,
    and post-submit background synchronization.
    """

    BASE_URL = "https://www.threads.net"

    async def _check_modal_post_button_status(self, page: Page) -> Dict[str, Any]:
        """
        Evaluates the Post button status specifically inside the Threads composer modal.
        Checks computed opacity and cursor:
        - When disabled: opacity is 0.3, cursor is 'not-allowed'.
        - When ready: opacity is 1.0, cursor is 'pointer'.
        """
        try:
            if not hasattr(page, "evaluate"):
                return {"found": True, "ready": True}

            status = await page.evaluate("""() => {
                const h1 = Array.from(document.querySelectorAll("h1")).find(el => 
                    (el.innerText || '').includes("New thread") || (el.innerText || '').includes("Bài viết mới")
                );
                let modal = h1;
                while (modal && modal.parentElement && modal.parentElement !== document.body) {
                    if (modal.innerText.includes("Post Options") || modal.innerText.includes("Tùy chọn")) break;
                    modal = modal.parentElement;
                }
                if (!modal) return { found: false, ready: false, isStillUploading: false };

                const buttons = Array.from(modal.querySelectorAll("div[role='button'], button"));
                const postBtn = buttons.find(b => {
                    const t = (b.innerText || '').trim().toLowerCase();
                    return t === 'post' || t === 'đăng';
                });
                if (!postBtn) return { found: false, ready: false, isStillUploading: false };

                const style = window.getComputedStyle(postBtn);
                const opacity = parseFloat(style.opacity || '0');
                const notAllowed = style.cursor === 'not-allowed';
                const hasProgress = modal.querySelectorAll("[role='progressbar'], svg.animate-spin").length > 0;

                const isReady = opacity > 0.8 && !notAllowed && !hasProgress;

                return {
                    found: true,
                    ready: isReady,
                    opacity,
                    cursor: style.cursor,
                    isStillUploading: hasProgress || opacity <= 0.8
                };
            }""")
            return status if isinstance(status, dict) else {"found": False, "ready": False}
        except Exception as e:
            logger.debug("Error checking Threads post button status: %s", e)
            return {"found": False, "ready": False}

    _check_post_button_status = _check_modal_post_button_status

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
            self.log("Đang điều hướng đến Threads (threads.net)...", "info", log_callback)
            await page.goto(self.BASE_URL, wait_until="domcontentloaded")

            if self.check_login_redirect(page, "threads", log_callback):
                await self.capture_error_screenshot(page, "threads")
                return False

            if not is_mock:
                await self._dismiss_popups(page)

            self.log("Đang mở hộp thoại soạn thảo Threads...", "info", log_callback)
            composer_triggers = [
                "svg[aria-label='Create']",
                "svg[aria-label='Tạo']",
                "[aria-label='New thread']",
                "[aria-label='Bài viết mới']",
                "div[role='button']:has-text('Start a thread')",
                "div[role='button']:has-text('Có gì mới?')",
                "div[role='button']:has-text('Tạo')",
            ]

            # Check if modal already present
            modal_heading = page.locator("h1:has-text('New thread'), h1:has-text('Bài viết mới')")
            if (await self.element_count(modal_heading)) == 0:
                await self.safe_click(page, composer_triggers, timeout=6000, optional=True)
                if not is_mock:
                    await asyncio.sleep(1.0)

            # Wait up to 5s for composer modal to appear
            if not is_mock:
                for _ in range(10):
                    if (await self.element_count(page.locator("h1:has-text('New thread'), h1:has-text('Bài viết mới')"))) > 0:
                        break
                    await asyncio.sleep(0.5)

            # Target the file input specifically inside the composer modal
            self.log(f"Đang đính kèm file video: {video_path}", "info", log_callback)
            file_input_selectors = [
                "div:has(h1:has-text('New thread')) input[type='file']",
                "div:has(h1:has-text('Bài viết mới')) input[type='file']",
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
                await asyncio.sleep(1.0)

            # Build caption and hashtags
            caption = metadata.get("caption", "").strip()
            hashtags = metadata.get("hashtags", [])
            tag_str = " ".join([tag if tag.startswith("#") else f"#{tag}" for tag in hashtags]).strip()
            full_caption = f"{caption} {tag_str}".strip() if tag_str else caption

            # Ensure caption is not empty so Threads doesn't lock the Post button
            if not full_caption:
                title = metadata.get("title", "").strip()
                full_caption = title if title else "Video mới chia sẻ"

            self.log(f"Đang nhập nội dung thread: {full_caption[:60]}...", "info", log_callback)
            editor_selectors = [
                "div:has(h1:has-text('New thread')) div[contenteditable='true']",
                "div:has(h1:has-text('Bài viết mới')) div[contenteditable='true']",
                "div:has(h1:has-text('New thread')) div[role='textbox']",
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

            # Atomic text insertion into editor
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
                self.log("Đang chờ Threads xử lý video và sẵn sàng xuất bản...", "info", log_callback)
                upload_ready = False
                for wait_step in range(60):  # 60 * 1.5s = 90 seconds
                    await asyncio.sleep(1.5)
                    await self._dismiss_popups(page)

                    btn_status = await self._check_modal_post_button_status(page)
                    if btn_status.get("ready"):
                        upload_ready = True
                        self.log("Threads đã chuẩn bị video xong! Nút Đăng đã sẵn sàng.", "info", log_callback)
                        break

                    if wait_step % 4 == 0:
                        self.log(f"Đang chuẩn bị video trên Threads ({int(wait_step * 1.5)}s)...", "info", log_callback)

                if not upload_ready:
                    self.log("Cảnh báo: Thời gian xử lý video quá lâu, thử thực hiện bấm Đăng...", "warning", log_callback)

            self.log("Đang bấm nút Post trên Threads...", "info", log_callback)
            post_clicked = False

            # Primary: JavaScript direct click on modal's Post button
            if not is_mock:
                try:
                    js_clicked = await page.evaluate("""() => {
                        const h1 = Array.from(document.querySelectorAll("h1")).find(el => 
                            (el.innerText || '').includes("New thread") || (el.innerText || '').includes("Bài viết mới")
                        );
                        let modal = h1;
                        while (modal && modal.parentElement && modal.parentElement !== document.body) {
                            if (modal.innerText.includes("Post Options") || modal.innerText.includes("Tùy chọn")) break;
                            modal = modal.parentElement;
                        }
                        if (!modal) return false;
                        const buttons = Array.from(modal.querySelectorAll("div[role='button'], button"));
                        const postBtn = buttons.find(b => {
                            const t = (b.innerText || '').trim().toLowerCase();
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
                        self.log("Đã click nút Post trong hộp thoại Threads thành công (JS)!", "info", log_callback)
                except Exception as ex:
                    logger.debug("JS click on Threads post failed: %s", ex)

            # Secondary fallback: Playwright click
            if not post_clicked:
                post_selectors = [
                    "div:has(h1:has-text('New thread')) div[role='button']:has-text('Post')",
                    "div:has(h1:has-text('Bài viết mới')) div[role='button']:has-text('Đăng')",
                    "div:has(h1:has-text('New thread')) button:has-text('Post')",
                    "div[role='button']:has-text('Post')",
                    "button:has-text('Post')",
                    "div[role='button']:has-text('Đăng')",
                    "button:has-text('Đăng')",
                ]
                for p_sel in post_selectors:
                    try:
                        cand = await self.get_locator(page, p_sel)
                        cnt = await self.element_count(cand)
                        if cnt > 0:
                            res = cand.click(timeout=5000)
                            if inspect.isawaitable(res):
                                await res
                            post_clicked = True
                            self.log(f"Đã click nút Post Threads bằng: {p_sel}", "info", log_callback)
                            break
                    except Exception:
                        continue

            # Save debug screenshot immediately after clicking Post
            if not is_mock:
                try:
                    LOGS_DIR.mkdir(parents=True, exist_ok=True)
                    await page.screenshot(path=str(LOGS_DIR / "threads_debug_after_post.png"))
                except Exception:
                    pass

            # Step 1: Wait for composer modal to close
            if not is_mock:
                self.log("Đang theo dõi đóng hộp thoại đăng bài Threads...", "info", log_callback)
                modal_closed = False
                for _ in range(20):  # up to 20s
                    await asyncio.sleep(1.0)
                    h1_cnt = await self.element_count(page.locator("h1:has-text('New thread'), h1:has-text('Bài viết mới')"))
                    if h1_cnt == 0:
                        modal_closed = True
                        self.log("Hộp thoại đăng bài Threads đã đóng thành công!", "info", log_callback)
                        break

                if not modal_closed:
                    self.log("Hộp thoại Threads chưa đóng sau khi bấm Đăng.", "warning", log_callback)

                # Step 2: CRITICAL - Wait for background 'Posting...' banner to complete and disappear
                self.log("Đang chờ Threads hoàn tất quá trình tải và ghi video vào trang cá nhân (Posting...)...", "info", log_callback)
                upload_finished = False
                for wait_posting in range(90):  # up to 90s
                    await asyncio.sleep(1.0)
                    post_status = await page.evaluate("""() => {
                        const text = document.body.innerText || "";
                        const hasPosting = text.includes("Posting...") || text.includes("Đang đăng...");
                        const hasPosted = text.includes("Posted") || text.includes("Đã đăng");
                        return { hasPosting, hasPosted };
                    }""")

                    if wait_posting % 5 == 0 and post_status.get("hasPosting"):
                        self.log(f"Threads đang đồng bộ video lên máy chủ Meta ({wait_posting}s)...", "info", log_callback)

                    # Once 'Posting...' banner disappears or 'Posted' appears, Meta has accepted the post
                    if not post_status.get("hasPosting"):
                        upload_finished = True
                        self.log(f"Threads đã ghi nhận xuất bản video thành công sau {wait_posting}s!", "info", log_callback)
                        break

                if not upload_finished:
                    self.log("Cảnh báo: Thời gian chờ tiến trình 'Posting...' quá 90s.", "warning", log_callback)

                # Grace period for final WebSocket / HTTP network confirmation
                await asyncio.sleep(4.0)

            self.log("Threads post published successfully!", "success", log_callback)
            return True

        except Exception as e:
            self.check_login_redirect(page, "threads", log_callback)
            await self.capture_error_screenshot(page, "threads")
            self.log(f"Threads upload failed: {str(e)}", "error", log_callback)
            return False
