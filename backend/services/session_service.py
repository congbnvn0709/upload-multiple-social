import json
import logging
import os
import shutil
import sqlite3
import tempfile
import threading
import time
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

# Authentication and session cookie indicators
PLATFORM_AUTH_CONFIG: Dict[str, Dict[str, list[str]]] = {
    "tiktok": {
        "domains": ["tiktok.com"],
        "cookies": ["sessionid", "sessionid_ss", "sid_guard", "sid_tt"],
    },
    "facebook": {
        "domains": ["facebook.com"],
        "cookies": ["c_user", "xs"],
    },
    "threads": {
        "domains": ["threads.net", "threads.com", "instagram.com"],
        "cookies": ["sessionid", "ds_user_id"],
    },
    "youtube": {
        "domains": ["youtube.com", "google.com"],
        "cookies": ["SID", "SSID", "LOGIN_INFO", "SAPISID", "APISID", "HSID"],
    },
}

# Global thread-safe management of interactive login window
_active_login_thread: Optional[threading.Thread] = None
_stop_login_event = threading.Event()
_active_browser_lock = threading.Lock()


def ensure_profile_unlocked(profile_dir: Optional[Path] = None) -> None:
    """
    Cleans up stale Chromium lock symlinks (SingletonLock, SingletonCookie, SingletonSocket)
    if the owning process is no longer alive, or terminates lingering Chrome-for-Testing processes.
    """
    target_dir = profile_dir if profile_dir is not None else BROWSER_PROFILE_DIR
    if not target_dir.exists():
        return

    lock_file = target_dir / "SingletonLock"
    if lock_file.is_symlink() or lock_file.exists():
        try:
            target = os.readlink(str(lock_file))
            if "-" in target:
                pid_str = target.rsplit("-", 1)[-1]
                if pid_str.isdigit():
                    pid = int(pid_str)
                    try:
                        os.kill(pid, 0)
                        logger.info("Found active browser process %d holding profile lock. Terminating...", pid)
                        os.kill(pid, 15)
                        time.sleep(0.5)
                        try:
                            os.kill(pid, 0)
                            os.kill(pid, 9)
                        except OSError:
                            pass
                    except OSError:
                        # Process not running; lock is stale
                        pass
        except Exception as e:
            logger.warning("Error inspecting SingletonLock: %s", e)

    for fname in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
        p = target_dir / fname
        try:
            if p.is_symlink() or p.exists():
                p.unlink(missing_ok=True)
        except Exception as e:
            logger.warning("Could not unlink %s: %s", fname, e)


def close_active_login_window() -> None:
    """
    Signals any currently active interactive login browser instance to gracefully close
    from its own worker thread, avoiding Greenlet cross-thread switching errors.
    """
    global _active_login_thread
    with _active_browser_lock:
        _stop_login_event.set()
        if _active_login_thread is not None and _active_login_thread.is_alive():
            _active_login_thread.join(timeout=2.0)
        _active_login_thread = None


def get_account_status(profile_dir: Optional[Path] = None) -> Dict[str, bool]:
    """
    Inspects the browser profile directory for stored authenticated session cookies
    to determine actual login status across platforms.
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

    found_cookies: set[tuple[str, str]] = set()

    # 1. Inspect storage_state.json / state.json if present
    for state_name in ["storage_state.json", "state.json"]:
        state_file = target_dir / state_name
        if state_file.is_file():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for cookie in data.get("cookies", []):
                    domain = cookie.get("domain", "").lower().lstrip(".")
                    name = cookie.get("name", "")
                    if domain and name:
                        found_cookies.add((domain, name))
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
                cursor.execute("SELECT host_key, name FROM cookies")
                for host, name in cursor.fetchall():
                    if host and name:
                        found_cookies.add((host.lower().lstrip("."), name))
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
                    cursor.execute("SELECT host_key, name FROM cookies")
                    for host, name in cursor.fetchall():
                        if host and name:
                            found_cookies.add((host.lower().lstrip("."), name))
                    conn.close()
                    os.remove(tmp_path)
                except Exception as e:
                    logger.warning("Error reading SQLite cookies from %s: %s", db_path, e)

    # Check for authentication cookies
    for platform, config in PLATFORM_AUTH_CONFIG.items():
        matched = any(
            any(d in stored_domain for d in config["domains"]) and stored_name in config["cookies"]
            for stored_domain, stored_name in found_cookies
        )
        status[platform] = matched

    return status


def _run_browser(platform: str, headless: bool, profile_dir: Path):
    """Worker function to launch Playwright persistent browser context for interactive login."""
    # Ensure stale locks are cleared
    ensure_profile_unlocked(profile_dir)
    profile_dir.mkdir(parents=True, exist_ok=True)
    url = LOGIN_URLS[platform]

    _stop_login_event.clear()

    pw = None
    context = None
    try:
        pw = sync_playwright().start()
        context = pw.chromium.launch_persistent_context(
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

        # Wait until user closes all windows or external stop signal is received
        while not _stop_login_event.is_set():
            try:
                pages_open = [p for p in context.pages if not p.is_closed()]
                if not pages_open:
                    break
                time.sleep(0.5)
            except Exception:
                break

        sync_state()

    except Exception as e:
        logger.error("Error running login browser for %s: %s", platform, e)
    finally:
        # Gracefully close context and Playwright from within the same thread
        try:
            if context is not None:
                context.close()
        except Exception:
            pass
        try:
            if pw is not None:
                pw.stop()
        except Exception:
            pass
        ensure_profile_unlocked(profile_dir)


def open_login_window(
    platform: str,
    headless: bool = False,
    profile_dir: Optional[Path] = None,
    block: bool = False,
) -> Optional[threading.Thread]:
    """
    Launch a headed Playwright browser instance with persistent context pointing to the platform's login page.
    Closes any previously open login window to prevent Chromium profile lock conflicts.
    """
    global _active_login_thread
    platform_key = platform.strip().lower()
    if platform_key not in LOGIN_URLS:
        raise ValueError(
            f"Unsupported platform '{platform}'. Supported platforms: {', '.join(LOGIN_URLS.keys())}"
        )

    target_dir = profile_dir if profile_dir is not None else BROWSER_PROFILE_DIR

    # Close previous login window if already open
    close_active_login_window()

    if block:
        _run_browser(platform_key, headless, target_dir)
        return None

    thread = threading.Thread(
        target=_run_browser,
        args=(platform_key, headless, target_dir),
        name=f"LoginWindow-{platform_key}",
        daemon=True,
    )
    with _active_browser_lock:
        _active_login_thread = thread
    thread.start()
    return thread
