import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.uploaders.base import BaseUploader, get_uploader
from backend.uploaders.tiktok import TikTokUploader
from backend.uploaders.threads import ThreadsUploader
from backend.uploaders.facebook import FacebookUploader
from backend.uploaders.youtube import YouTubeUploader


def test_uploader_registry():
    uploader = get_uploader("tiktok")
    assert isinstance(uploader, TikTokUploader)
    assert isinstance(uploader, BaseUploader)

    threads_uploader = get_uploader("threads")
    assert isinstance(threads_uploader, ThreadsUploader)
    assert isinstance(threads_uploader, BaseUploader)

    fb_uploader = get_uploader("facebook")
    assert isinstance(fb_uploader, FacebookUploader)
    assert isinstance(fb_uploader, BaseUploader)

    yt_uploader = get_uploader("youtube")
    assert isinstance(yt_uploader, YouTubeUploader)
    assert isinstance(yt_uploader, BaseUploader)

    with pytest.raises(ValueError):
        get_uploader("unsupported_platform")


@pytest.mark.asyncio
async def test_base_uploader_type_humanized():
    uploader = TikTokUploader()
    mock_page = AsyncMock()
    mock_locator = AsyncMock()
    mock_page.locator = MagicMock(return_value=mock_locator)

    await uploader.type_humanized(mock_page, "input#test", "hello", min_delay=0.001, max_delay=0.002)
    mock_locator.click.assert_awaited_once()
    assert mock_page.keyboard.press.await_count == 5


@pytest.mark.asyncio
async def test_tiktok_uploader_mock():
    uploader = TikTokUploader()
    mock_page = AsyncMock()
    mock_file_input = AsyncMock()
    mock_caption_box = AsyncMock()
    mock_post_button = AsyncMock()

    def mock_locator(selector):
        if "input[type='file']" in selector or 'input[type="file"]' in selector:
            return mock_file_input
        elif "public-DraftEditor-content" in selector or "contenteditable" in selector:
            return mock_caption_box
        elif "Post" in selector or "post" in selector:
            return mock_post_button
        return AsyncMock()

    mock_page.locator = MagicMock(side_effect=mock_locator)

    logs = []
    def log_cb(msg, status="info"):
        logs.append((msg, status))

    metadata = {
        "caption": "Awesome test video! Check it out",
        "hashtags": ["#fyp", "#viral"],
    }

    result = await uploader.upload(mock_page, "/tmp/test.mp4", metadata, log_callback=log_cb)
    assert result is True
    mock_page.goto.assert_awaited()
    assert any("tiktok.com" in call.args[0] for call in mock_page.goto.await_args_list)
    assert mock_file_input.set_input_files.awaited
    assert len(logs) > 0


@pytest.mark.asyncio
async def test_threads_uploader_mock():
    uploader = ThreadsUploader()
    mock_page = AsyncMock()
    mock_file_input = AsyncMock()
    mock_caption_box = AsyncMock()
    mock_post_button = AsyncMock()

    def mock_locator(selector):
        if "input[type='file']" in selector or 'input[type="file"]' in selector:
            return mock_file_input
        elif "contenteditable" in selector or "textbox" in selector or "textarea" in selector:
            return mock_caption_box
        elif "Post" in selector or "Đăng" in selector:
            return mock_post_button
        return AsyncMock()

    mock_page.locator = MagicMock(side_effect=mock_locator)

    logs = []
    def log_cb(msg, status="info"):
        logs.append((msg, status))

    metadata = {
        "caption": "Threads test post",
        "hashtags": ["#threads", "#viral"],
    }

    result = await uploader.upload(mock_page, "/tmp/test.mp4", metadata, log_callback=log_cb)
    assert result is True
    mock_page.goto.assert_awaited()
    assert any("threads.net" in call.args[0] for call in mock_page.goto.await_args_list)
    assert mock_file_input.set_input_files.awaited
    assert len(logs) > 0


@pytest.mark.asyncio
async def test_facebook_uploader_mock_profile():
    uploader = FacebookUploader()
    mock_page = AsyncMock()
    mock_file_input = AsyncMock()
    mock_caption_box = AsyncMock()
    mock_next_button = AsyncMock()
    mock_publish_button = AsyncMock()

    def mock_locator(selector):
        if "input[type='file']" in selector or 'input[type="file"]' in selector:
            return mock_file_input
        elif "contenteditable" in selector or "textbox" in selector or "textarea" in selector:
            return mock_caption_box
        elif "Next" in selector or "Tiếp" in selector:
            return mock_next_button
        elif "Publish" in selector or "Đăng" in selector:
            return mock_publish_button
        return AsyncMock()

    mock_page.locator = MagicMock(side_effect=mock_locator)

    logs = []
    metadata = {
        "target": "profile",
        "caption": "Reels post description",
        "hashtags": ["#facebookreels"],
    }

    result = await uploader.upload(mock_page, "/tmp/test.mp4", metadata, log_callback=lambda m, s="info": logs.append((m, s)))
    assert result is True
    assert any("facebook.com" in call.args[0] for call in mock_page.goto.await_args_list)
    assert mock_file_input.set_input_files.awaited
    assert len(logs) > 0


@pytest.mark.asyncio
async def test_facebook_uploader_mock_fanpage():
    uploader = FacebookUploader()
    mock_page = AsyncMock()
    mock_file_input = AsyncMock()
    mock_caption_box = AsyncMock()
    mock_publish_button = AsyncMock()

    def mock_locator(selector):
        if "input[type='file']" in selector:
            return mock_file_input
        elif "contenteditable" in selector:
            return mock_caption_box
        elif "Publish" in selector or "Đăng" in selector:
            return mock_publish_button
        return AsyncMock()

    mock_page.locator = MagicMock(side_effect=mock_locator)

    logs = []
    metadata = {
        "target": "fanpage",
        "page_id": "123456789",
        "caption": "Fanpage video",
        "hashtags": ["#page"],
    }

    result = await uploader.upload(mock_page, "/tmp/test.mp4", metadata, log_callback=lambda m, s="info": logs.append((m, s)))
    assert result is True
    assert any("123456789" in call.args[0] for call in mock_page.goto.await_args_list)
    assert len(logs) > 0


@pytest.mark.asyncio
async def test_youtube_uploader_mock():
    uploader = YouTubeUploader()
    mock_page = AsyncMock()
    mock_file_input = AsyncMock()
    mock_title_box = AsyncMock()
    mock_desc_box = AsyncMock()
    mock_not_kids_radio = AsyncMock()
    mock_next_btn = AsyncMock()
    mock_public_radio = AsyncMock()
    mock_publish_btn = AsyncMock()

    def mock_locator(selector):
        if "input[type='file']" in selector or 'input[type="file"]' in selector:
            return mock_file_input
        elif "textbox" in selector and "title" in selector.lower():
            return mock_title_box
        elif "description" in selector.lower():
            return mock_desc_box
        elif "made-for-kids" in selector.lower() or "not_for_kids" in selector.lower():
            return mock_not_kids_radio
        elif "next-button" in selector.lower() or "next" in selector.lower():
            return mock_next_btn
        elif "public" in selector.lower():
            return mock_public_radio
        elif "done-button" in selector.lower() or "publish" in selector.lower():
            return mock_publish_btn
        return AsyncMock()

    mock_page.locator = MagicMock(side_effect=mock_locator)

    logs = []
    metadata = {
        "title": "A super catchy title for YouTube Shorts",
        "description": "Full description with keywords",
        "tags": ["shorts", "coding"],
        "visibility": "public"
    }

    result = await uploader.upload(mock_page, "/tmp/test.mp4", metadata, log_callback=lambda m, s="info": logs.append((m, s)))
    assert result is True
    assert any("studio.youtube.com" in call.args[0] for call in mock_page.goto.await_args_list)
    assert mock_file_input.set_input_files.awaited
    assert len(logs) > 0


@pytest.mark.asyncio
async def test_uploader_error_handling():
    uploader = TikTokUploader()
    mock_page = AsyncMock()
    mock_page.goto.side_effect = Exception("Network connection lost")

    logs = []
    result = await uploader.upload(mock_page, "/tmp/test.mp4", {}, log_callback=lambda m, s="info": logs.append((m, s)))
    assert result is False
    assert any("failed" in msg.lower() for msg, s in logs)
    assert any(s == "error" for msg, s in logs)

