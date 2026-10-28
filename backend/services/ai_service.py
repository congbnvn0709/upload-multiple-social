import inspect
import json
import logging
import re
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from backend.config import GEMINI_API_KEY

logger = logging.getLogger(__name__)


class GenerateCaptionsRequest(BaseModel):
    topic: str = Field(..., min_length=1, description="Topic or prompt for video captions")

    @field_validator("topic")
    @classmethod
    def validate_topic_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Topic must not be empty or whitespace only.")
        return stripped


class PlatformCaption(BaseModel):
    caption: str
    hashtags: List[str]


class YouTubeCaption(BaseModel):
    title: str
    description: str
    tags: List[str]


class CaptionsResponse(BaseModel):
    tiktok: PlatformCaption
    threads: PlatformCaption
    facebook: PlatformCaption
    youtube: YouTubeCaption


SYSTEM_INSTRUCTION = """You are a senior social media content strategist specializing in short-form vertical videos (TikTok, Threads, Facebook Reels, YouTube Shorts).
Your task is to generate platform-tailored, highly engaging Vietnamese captions, titles, hashtags, and tags for a given video topic.

Platform Style Profiles:
1. TikTok:
   - Dynamic, high-energy hook in the first line.
   - Concise body, relatable tone with emojis.
   - 4-5 relevant viral hashtags including #fyp, #xuhuong, and topic-specific hashtags.

2. Threads:
   - Thought-provoking, conversational starter asking an engaging open-ended question.
   - Clean formatting, natural community discussion tone.
   - 2-4 focused hashtags.

3. Facebook:
   - Informative, warm, narrative-driven or story-telling style.
   - Clear paragraph structure with spacing and a call-to-action (like, share, save).
   - 3-5 high-engagement hashtags.

4. YouTube (Shorts):
   - title: Catchy, clickable title under 100 characters, ending with #Shorts.
   - description: Engaging summary highlighting the key takeaway with call-to-action to subscribe, including relevant hashtags.
   - tags: 4-6 concise keyword tags for YouTube search SEO.

Output must strictly conform to the JSON schema.
"""


def _clean_hashtag(topic: str) -> str:
    """Extract a CamelCase hashtag from the topic."""
    words = re.findall(r"\w+", topic)
    if not words:
        return "trend"
    return "".join(w.capitalize() for w in words[:4])


def generate_fallback_captions(topic: str) -> dict:
    """Generate high-quality platform-specific fallback captions when AI is offline or without API key."""
    clean_tag = _clean_hashtag(topic)
    return {
        "tiktok": {
            "caption": f"🔥 Bí quyết cực hay về {topic} mà bạn không nên bỏ lỡ! Xem ngay đến cuối video để áp dụng ngay hôm nay nhé 🚀",
            "hashtags": [f"#{clean_tag}", "#viral", "#trending", "#fyp", "#xuhuong"],
        },
        "threads": {
            "caption": f"Góc thảo luận: Quan điểm của bạn thế nào về {topic}?\n\nCùng chia sẻ góc nhìn và trải nghiệm của bạn dưới phần bình luận nhé! 👇",
            "hashtags": [f"#{clean_tag}", "#discussion", "#insights", "#trending"],
        },
        "facebook": {
            "caption": f"Chia sẻ hữu ích về {topic} dành cho tất cả mọi người.\n\nNếu bạn đang tìm hiểu hoặc quan tâm đến chủ đề này, đừng quên lưu lại và chia sẻ video để cùng thảo luận nhé! ✨",
            "hashtags": [f"#{clean_tag}", "#chiase", "#kienthuc", "#xuhuong"],
        },
        "youtube": {
            "title": f"{topic} trong 60 giây | Bạn đã biết chưa? #Shorts",
            "description": f"Tất tần tật những điều bạn cần biết về {topic}. Hãy like và subscribe để theo dõi thêm nhiều video hữu ích mỗi ngày!\n\n#Shorts #xuhuong #{clean_tag}",
            "tags": [clean_tag.lower(), "shorts", "trending", "kienthuc", "huongdan"],
        },
    }


def get_gemini_client():
    """Instantiate and return the google.genai Client."""
    from google import genai
    return genai.Client(api_key=GEMINI_API_KEY)


def _clean_json_text(text: str) -> str:
    """Strip markdown code fence blocks if present."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def generate_captions_for_topic(topic: str) -> dict:
    """Generate platform-tailored social captions using Gemini or fallback template generator."""
    # Check if API key is provided
    from backend.config import GEMINI_API_KEY as CURRENT_API_KEY
    api_key = globals().get("GEMINI_API_KEY", CURRENT_API_KEY)

    if not api_key or not str(api_key).strip():
        logger.info("GEMINI_API_KEY is not configured. Using fallback templates.")
        return generate_fallback_captions(topic)

    try:
        from google.genai import types

        client = get_gemini_client()
        prompt = f"Tạo caption và hashtag cho video ngắn với chủ đề: {topic}"

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=CaptionsResponse,
            temperature=0.7,
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=config,
        )

        raw_text = _clean_json_text(response.text or "")
        data = json.loads(raw_text)
        validated = CaptionsResponse(**data)
        return validated.model_dump()
    except Exception as exc:
        logger.warning("Gemini caption generation encountered error (%s). Falling back to templates.", exc)
        return generate_fallback_captions(topic)
