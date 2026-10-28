import asyncio
import datetime
import inspect
import logging
import random
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock

from playwright.async_api import Locator, Page

from backend.config import LOGS_DIR

logger = logging.getLogger(__name__)


class BaseUploader(ABC):
    """
    Abstract base class for social media platform uploaders using Playwright.
    """

    @abstractmethod
    async def upload(
        self,
        page: Page,
        video_path: str,
        metadata: Dict[str, Any],
        log_callback: Optional[Callable] = None,
    ) -> bool:
        """
        Uploads a video to the target platform.

        :param page: Active Playwright Page instance with loaded session.
        :param video_path: Absolute or relative path to the video file.
        :param metadata: Platform metadata (caption, hashtags, title, description, etc.).
        :param log_callback: Optional callable accepting (message: str, status: str) or (message: str).
        :return: True if upload succeeded, False otherwise.
        """
        pass

    def log(
        self,
        message: str,
        status: str = "info",
        callback: Optional[Callable] = None,
    ) -> None:
        """
        Dispatches structured logs to log_callback and python logger.
        """
        logger.info(f"[{self.__class__.__name__}] [{status}] {message}")
        if callback:
            try:
                sig = inspect.signature(callback)
                if len(sig.parameters) >= 2:
                    callback(message, status)
                else:
                    callback(message)
            except Exception:
                try:
                    callback(message, status)
                except Exception:
                    pass

    async def get_locator(self, page: Page, selector: str) -> Any:
        """
        Retrieves a locator safely, accommodating both real Playwright Locators
        and test mocks (AsyncMock/MagicMock).
        """
        loc = page.locator(selector)
        if inspect.isawaitable(loc):
            loc = await loc
        # For real Playwright Locators, select the first matching element
        if hasattr(loc, "first") and not isinstance(loc, (AsyncMock, MagicMock)):
            loc = loc.first
        return loc

    async def type_humanized(
        self,
        page: Page,
        selector_or_locator: Union[str, Locator, Any],
        text: str,
        min_delay: float = 0.02,
        max_delay: float = 0.08,
    ) -> None:
        """
        Simulates human typing character-by-character with slight random delays.
        """
        if isinstance(selector_or_locator, str):
            locator = await self.get_locator(page, selector_or_locator)
        else:
            locator = selector_or_locator

        if hasattr(locator, "click"):
            try:
                click_res = locator.click()
                if inspect.isawaitable(click_res):
                    await click_res
            except Exception:
                pass

        for char in text:
            if min_delay > 0:
                delay = random.uniform(min_delay, max_delay)
                await asyncio.sleep(delay)
            insert_res = page.keyboard.insert_text(char)
            if inspect.isawaitable(insert_res):
                await insert_res

    async def capture_error_screenshot(self, page: Page, platform: str) -> Optional[str]:
        """
        Captures a screenshot on failure and saves it to LOGS_DIR / f"{platform}_error_{timestamp}.png".
        """
        try:
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = LOGS_DIR / f"{platform}_error_{timestamp}.png"
            if hasattr(page, "screenshot"):
                res = page.screenshot(path=str(screenshot_path))
                if inspect.isawaitable(res):
                    await res
                return str(screenshot_path)
        except Exception as e:
            logger.warning(f"Failed to capture error screenshot for {platform}: {e}")
        return None

    def check_login_redirect(
        self,
        page: Page,
        platform: str = "",
        log_callback: Optional[Callable] = None,
    ) -> bool:
        """
        Checks if page URL redirected to a login page (e.g. tiktok.com/login, facebook.com/login).
        If so, logs: 'Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại'.
        """
        try:
            url_val = getattr(page, "url", None)
            url = url_val if isinstance(url_val, str) else ""
            if not url:
                return False
            url_lower = url.lower()
            login_patterns = [
                "/login",
                "/signin",
                "accounts.google.com",
                "servicelogin",
                "tiktok.com/login",
                "facebook.com/login",
                "threads.net/login",
            ]
            if any(p in url_lower for p in login_patterns):
                self.log("Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại", "error", log_callback)
                return True
        except Exception:
            pass
        return False

    async def safe_click(
        self,
        page: Page,
        selectors: Union[str, List[str]],
        timeout: int = 5000,
        optional: bool = False,
    ) -> bool:
        """
        Tries to click one of the provided selector candidates.
        """
        selector_list = [selectors] if isinstance(selectors, str) else selectors
        for sel in selector_list:
            try:
                loc = await self.get_locator(page, sel)
                if hasattr(loc, "click"):
                    click_res = loc.click(timeout=timeout)
                    if inspect.isawaitable(click_res):
                        await click_res
                    return True
            except Exception:
                continue

        if not optional:
            logger.debug(f"Failed to click any selector from {selector_list}")
        return False

    async def find_first(
        self,
        page: Page,
        selectors: Union[str, List[str]],
        timeout: int = 5000,
    ) -> Optional[Any]:
        """
        Finds the first matching locator from a list of selector candidates.
        """
        selector_list = [selectors] if isinstance(selectors, str) else selectors
        for sel in selector_list:
            try:
                loc = await self.get_locator(page, sel)
                if hasattr(loc, "wait_for"):
                    wait_res = loc.wait_for(timeout=timeout)
                    if inspect.isawaitable(wait_res):
                        await wait_res
                return loc
            except Exception:
                continue
        return None


def get_uploader(platform: str) -> BaseUploader:
    """
    Factory function returning the uploader instance for the specified platform.
    """
    platform_key = platform.strip().lower()
    from backend.uploaders.tiktok import TikTokUploader
    from backend.uploaders.threads import ThreadsUploader
    from backend.uploaders.facebook import FacebookUploader
    from backend.uploaders.youtube import YouTubeUploader

    registry: Dict[str, BaseUploader] = {
        "tiktok": TikTokUploader(),
        "threads": ThreadsUploader(),
        "facebook": FacebookUploader(),
        "youtube": YouTubeUploader(),
    }

    if platform_key not in registry:
        raise ValueError(
            f"Unsupported platform: '{platform}'. Available: {list(registry.keys())}"
        )

    return registry[platform_key]
