"""
Narration generation service using DashScope LLM.
Generates professional and casual style narrations for artworks.
"""

import os
from typing import Optional
from config import config
from .modelscope_client import get_modelscope_client


# Load prompt templates
PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")


def load_prompt(filename: str) -> str:
    """Load prompt template from file."""
    filepath = os.path.join(PROMPTS_DIR, filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


class NarrationService:
    """Service for generating artwork narrations."""

    STYLES = {
        "professional": {
            "prompt_file": "professional.txt",
            "max_length": 300,
            "voice": "zhichu"
        },
        "casual": {
            "prompt_file": "casual.txt",
            "max_length": 200,
            "voice": "zhibei"
        }
    }

    # Default prompts as fallback
    DEFAULT_PROFESSIONAL_PROMPT = """你是一位资深的艺术史专家和博物馆讲解员。请为以下艺术品撰写专业讲解词。

艺术品信息：
- 名称：{name}
- 作者：{artist}
- 年代：{year}
- 流派：{style}

要求：
1. 讲解词约 300 字
2. 重点介绍艺术技法、流派特点和历史地位
3. 使用专业但易懂的语言
4. 可适当引用艺术评论家的评价"""

    DEFAULT_CASUAL_PROMPT = """你是一位幽默风趣的博物馆导游，擅长用轻松有趣的方式讲述艺术品背后的故事。

艺术品信息：
- 名称：{name}
- 作者：{artist}
- 年代：{year}

要求：
1. 讲解词约 200 字
2. 可以分享创作者的趣闻轶事
3. 使用第一人称，仿佛艺术品在自我介绍
4. 语言活泼，适合年轻观众"""

    def __init__(self):
        """Initialize narration service."""
        self._load_prompts()
        self.modelscope = get_modelscope_client()

    def _load_prompts(self):
        """Load prompt templates from files."""
        self.prompts = {}

        # Try to load from files first
        professional = load_prompt("professional.txt")
        casual = load_prompt("casual.txt")

        # Use defaults if files not found
        self.prompts["professional"] = (
            professional if professional else self.DEFAULT_PROFESSIONAL_PROMPT
        )
        self.prompts["casual"] = (
            casual if casual else self.DEFAULT_CASUAL_PROMPT
        )

    async def generate_narration(
        self,
        artwork: dict,
        style: str = "professional"
    ) -> dict:
        """
        Generate narration for an artwork.

        Args:
            artwork: Artwork dictionary with name_cn, artist, year, style
            style: "professional" or "casual"

        Returns:
            dict with narration text or error
        """
        if style not in self.STYLES:
            return {
                "success": False,
                "error": f"Unknown style: {style}"
            }

        # Check if pre-written narration exists
        narration_key = f"description_{style}"
        if artwork.get(narration_key):
            return {
                "success": True,
                "source": "cached",
                "narration": artwork[narration_key]
            }

        # Generate new narration
        return await self._generate_with_llm(artwork, style)

    async def _generate_with_llm(
        self,
        artwork: dict,
        style: str
    ) -> dict:
        """Generate narration using LLM."""
        try:
            # Format prompt with artwork info
            prompt_template = self.prompts[style]
            prompt = prompt_template.format(
                name=artwork.get("name_cn", "Unknown"),
                artist=artwork.get("artist", "Unknown"),
                year=artwork.get("year", "Unknown"),
                style=artwork.get("style", "Unknown")
            )
            description = (
                artwork.get("description_casual")
                or artwork.get("description_professional")
                or ""
            ).strip()
            if description:
                prompt = f"{prompt}\n\n补充信息：\n- 简述：{description}"

            response = await self.modelscope.chat_completions(
                model=config.NARRATION_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.7,
                enable_thinking=False
            )

            if response["status_code"] == 200:
                data = response["data"]
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                if isinstance(content, list):
                    parts = []
                    for item in content:
                        if isinstance(item, dict):
                            text = item.get("text")
                            if text:
                                parts.append(text)
                        elif isinstance(item, str):
                            parts.append(item)
                    narration = "\n".join(parts)
                else:
                    narration = content
                return {
                    "success": True,
                    "source": "generated",
                    "narration": narration.strip()
                }
            else:
                return {
                    "success": False,
                    "error": f"LLM call failed: {response.get('data')}"
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Narration generation error: {str(e)}"
            }

    def get_voice_for_style(self, style: str) -> str:
        """Get TTS voice for narration style."""
        return self.STYLES.get(style, {}).get(
            "voice",
            config.TTS_PROFESSIONAL_VOICE
        )


# Singleton instance
_service: Optional[NarrationService] = None


def get_narration_service() -> NarrationService:
    """Get or create narration service singleton."""
    global _service
    if _service is None:
        _service = NarrationService()
    return _service
