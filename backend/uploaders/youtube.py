import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, Optional

from playwright.async_api import Page

from backend.uploaders.base import BaseUploader

logger = logging.getLogger(__name__)


class YouTubeUploader(BaseUploader):
    """
    Automated video publisher for YouTube Studio (Shorts and Videos).
    """

    STUDIO_URL = "https://studio.youtube.com"

    async def upload(
        self,
        page: Page,
        video_path: str,
        metadata: Dict[str, Any],
        log_callback: Optional[Callable] = None,
    ) -> bool:
        try:
            self.log("Navigating to YouTube Studio...", "info", log_callback)
            await page.goto(self.STUDIO_URL, wait_until="domcontentloaded")

            if self.check_login_redirect(page, "youtube", log_callback):
                await self.capture_error_screenshot(page, "youtube")
                return False

            self.log("Opening YouTube upload dialog...", "info", log_callback)
            create_buttons = [
                "#create-icon",
                "ytcp-button#create-icon",
                "tp-yt-paper-button:has-text('Create')",
                "button:has-text('Create')",
                "button:has-text('Tạo')",
                "#upload-icon",
                "ytcp-icon-button#upload-button",
            ]
            await self.safe_click(page, create_buttons, timeout=5000, optional=True)

            upload_item_selectors = [
                "tp-yt-paper-item:has-text('Upload videos')",
                "tp-yt-paper-item:has-text('Tải video lên')",
                "tp-yt-paper-item:has-text('Upload video')",
            ]
            await self.safe_click(page, upload_item_selectors, timeout=4000, optional=True)

            self.log(f"Attaching video file: {video_path}", "info", log_callback)
            file_input_selectors = [
                "input[type='file'][accept*='video']",
                "input[type='file']",
            ]
            file_input = await self.find_first(page, file_input_selectors, timeout=12000)
            if not file_input:
                file_input = await self.get_locator(page, "input[type='file']")

            if hasattr(file_input, "set_input_files"):
                set_res = file_input.set_input_files(video_path)
                if inspect.isawaitable(set_res):
                    await set_res
            else:
                await page.set_input_files("input[type='file']", video_path)

            self.log("Waiting for video metadata editor to appear...", "info", log_callback)
            await asyncio.sleep(0.5)

            # Title (< 100 characters)
            raw_title = metadata.get("title") or metadata.get("caption") or "Untitled Video"
            title = raw_title.strip()[:100]

            self.log(f"Setting title: {title}", "info", log_callback)
            title_selectors = [
                "div#textbox[aria-label*='Title']",
                "div#textbox[aria-label*='Tiêu đề']",
                "ytcp-social-suggestions-textbox[aria-label*='Title'] div#textbox",
                "div#title-textarea div#textbox",
                "div[aria-label*='Title']",
            ]
            title_loc = await self.find_first(page, title_selectors, timeout=10000)
            if not title_loc:
                title_loc = await self.get_locator(page, "div#textbox[aria-label*='Title']")

            try:
                click_res = title_loc.click()
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

            await self.type_humanized(page, title_loc, title, min_delay=0.001, max_delay=0.01)

            # Description + Tags
            raw_desc = metadata.get("description", "")
            tags = metadata.get("tags", [])
            tag_str = " ".join([tag if tag.startswith("#") else f"#{tag}" for tag in tags]).strip()
            full_desc = f"{raw_desc}\n\n{tag_str}".strip() if tag_str else raw_desc

            if full_desc:
                self.log("Entering description...", "info", log_callback)
                desc_selectors = [
                    "ytcp-social-suggestions-textbox[aria-label*='Description'] div#textbox",
                    "div#description-textarea div#textbox",
                    "div#textbox[aria-label*='Description']",
                    "div#textbox[aria-label*='Mô tả']",
                ]
                desc_loc = await self.find_first(page, desc_selectors, timeout=6000)
                if desc_loc:
                    await self.type_humanized(page, desc_loc, full_desc, min_delay=0.001, max_delay=0.01)

            # Made for Kids Selection: "No, it's not made for kids"
            self.log("Selecting 'Not made for kids'...", "info", log_callback)
            not_kids_selectors = [
                "tp-yt-paper-radio-button[name='VIDEO_MADE_FOR_KIDS_NOT_MFK']",
                "tp-yt-paper-radio-button[name*='NOT_MADE_FOR_KIDS']",
                "tp-yt-paper-radio-button:has-text(\"No, it's not made for kids\")",
                "tp-yt-paper-radio-button:has-text('Không, đây không phải nội dung dành cho trẻ em')",
            ]
            await self.safe_click(page, not_kids_selectors, timeout=8000, optional=True)

            # Next buttons through wizard steps (Monetization/Video elements, Checks, Visibility)
            self.log("Advancing through wizard steps...", "info", log_callback)
            next_selectors = [
                "#next-button",
                "ytcp-button#next-button",
                "tp-yt-paper-button:has-text('Next')",
                "button:has-text('Next')",
                "button:has-text('Tiếp')",
            ]

            for step in range(3):
                clicked_next = await self.safe_click(page, next_selectors, timeout=3000, optional=True)
                if clicked_next:
                    await asyncio.sleep(0.5)
                else:
                    break

            # Visibility Step
            visibility = metadata.get("visibility", "public").lower()
            self.log(f"Setting visibility to {visibility}...", "info", log_callback)
            if visibility == "unlisted":
                vis_selectors = [
                    "tp-yt-paper-radio-button[name='UNLISTED']",
                    "tp-yt-paper-radio-button:has-text('Unlisted')",
                    "tp-yt-paper-radio-button:has-text('Không công khai')",
                ]
            elif visibility == "private":
                vis_selectors = [
                    "tp-yt-paper-radio-button[name='PRIVATE']",
                    "tp-yt-paper-radio-button:has-text('Private')",
                    "tp-yt-paper-radio-button:has-text('Riêng tư')",
                ]
            else:
                vis_selectors = [
                    "tp-yt-paper-radio-button[name='PUBLIC']",
                    "tp-yt-paper-radio-button:has-text('Public')",
                    "tp-yt-paper-radio-button:has-text('Công khai')",
                ]

            await self.safe_click(page, vis_selectors, timeout=6000, optional=True)

            # Publish / Save / Done
            self.log("Saving / Publishing YouTube video...", "info", log_callback)
            publish_selectors = [
                "#done-button",
                "ytcp-button#done-button",
                "tp-yt-paper-button:has-text('Publish')",
                "tp-yt-paper-button:has-text('Save')",
                "button:has-text('Publish')",
                "button:has-text('Save')",
                "button:has-text('Xuất bản')",
                "button:has-text('Lưu')",
            ]
            clicked_pub = await self.safe_click(page, publish_selectors, timeout=8000)
            if not clicked_pub:
                loc = await self.get_locator(page, "#done-button, ytcp-button#done-button")
                if hasattr(loc, "click"):
                    res = loc.click()
                    if inspect.isawaitable(res):
                        await res

            self.log("YouTube video published / scheduled successfully!", "success", log_callback)
            return True

        except Exception as e:
            self.check_login_redirect(page, "youtube", log_callback)
            await self.capture_error_screenshot(page, "youtube")
            self.log(f"YouTube upload failed: {str(e)}", "error", log_callback)
            return False
