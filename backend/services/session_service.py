import json
import logging
import os
import shutil
import sqlite3
import tempfile
import threading
from pathlib import Path
from typing import Optional, Dict

from playwright.sync_api import sync_playwright

from backend.config import BROWSER_PROFILE_DIR

logger = logging.getLogger(__name__)

LOGIN_URLS: Dict[str, str] = {
    "tiktok": "https://www.tiktok.com/login",
    "threads": "https://www.threads.net/login",
    "facebook": "https://www.facebook.com/login",
    "youtube": "https://studio.youtube.com/",
}

PLATFORM_DOMAINS: Dict[str, list[str]] = {
    "tiktok": ["tiktok.com"],
    "threads": ["threads.net", "instagram.com"],
    "facebook": ["facebook.com"],
    "youtube": ["youtube.com"],
}


def get_account_status(profile_dir: Optional[Path] = None) -> Dict[str, bool]:
    """
    Inspect the browser profile directory for stored session cookies
    to determine authentication status for each social platform.
    """
    target_dir = profile_dir if profile_dir is not None else BROWSER_PROFILE_DIR
    status: Dict[str, bool] = {
        "tiktok": False,
        "threads": False,
        "facebook": False,
        "youtube": False,
    }

    if not target_dir.exists():
        return status

    found_domains: set[str] = set()

    # 1. Inspect storage_state.json / state.json if present
    for state_name in ["storage_state.json", "state.json"]:
        state_file = target_dir / state_name
        if state_file.is_file():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for cookie in data.get("cookies", []):
                    domain = cookie.get("domain", "").lower().lstrip(".")
                    if domain:
                        found_domains.add(domain)
                for origin in data.get("origins", []):
                    origin_str = origin.get("origin", "").lower()
                    if origin_str:
                        found_domains.add(origin_str)
            except Exception as e:
                logger.warning("Error reading state file %s: %s", state_file, e)

    # 2. Inspect Chromium SQLite Cookies database if present
    candidate_dbs = [
        target_dir / "Default" / "Network" / "Cookies",
        target_dir / "Default" / "Cookies",
        target_dir / "Cookies",
    ]

    for db_path in candidate_dbs:
        if db_path.is_file():
            read_success = False
            try:
                conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT host_key FROM cookies")
                for (host,) in cursor.fetchall():
                    if host:
                        found_domains.add(host.lower().lstrip("."))
                conn.close()
                read_success = True
            except Exception:
                read_success = False

            # If locked by running browser, copy to a temp file and query
            if not read_success:
                try:
                    with tempfile.NamedTemporaryFile(delete=False) as tmp:
                        tmp_path = tmp.name
                    shutil.copy2(db_path, tmp_path)
                    conn = sqlite3.connect(tmp_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT DISTINCT host_key FROM cookies")
                    for (host,) in cursor.fetchall():
                        if host:
                            found_domains.add(host.lower().lstrip("."))
                    conn.close()
                    os.remove(tmp_path)
                except Exception as e:
                    logger.warning("Error reading SQLite cookies from %s: %s", db_path, e)

    # Match discovered domains against platforms
    for platform, domains in PLATFORM_DOMAINS.items():
        matched = any(
            any(d in stored_domain for stored_domain in found_domains)
            for d in domains
        )
        status[platform] = matched

    return status


def _run_browser(platform: str, headless: bool, profile_dir: Path):
    """Worker function to launch Playwright persistent browser context for interactive login."""
    profile_dir.mkdir(parents=True, exist_ok=True)
    url = LOGIN_URLS[platform]

    try:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=headless,
                args=["--start-maximized"],
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(url)

            def sync_state():
                try:
                    state_file = profile_dir / "storage_state.json"
                    context.storage_state(path=str(state_file))
                except Exception:
                    pass

            # Sync session state on navigation
            page.on("framenavigated", lambda frame: sync_state())

            # Keep window open until user closes browser or context closes
            try:
                context.wait_for_event("close", timeout=0)
            except Exception:
                pass
            finally:
                sync_state()
    except Exception as e:
        logger.error("Error running login browser for %s: %s", platform, e)


def open_login_window(
    platform: str,
    headless: bool = False,
    profile_dir: Optional[Path] = None,
    block: bool = False,
) -> Optional[threading.Thread]:
    """
    Launch a headed Playwright browser instance with persistent context pointing to the platform's login page.
    Runs in a background thread by default so it does not block HTTP requests.
    """
    platform_key = platform.strip().lower()
    if platform_key not in LOGIN_URLS:
        raise ValueError(
            f"Unsupported platform '{platform}'. Supported platforms: {', '.join(LOGIN_URLS.keys())}"
        )

    target_dir = profile_dir if profile_dir is not None else BROWSER_PROFILE_DIR

    if block:
        _run_browser(platform_key, headless, target_dir)
        return None

    thread = threading.Thread(
        target=_run_browser,
        args=(platform_key, headless, target_dir),
        name=f"LoginWindow-{platform_key}",
        daemon=True,
    )
    thread.start()
    return thread
