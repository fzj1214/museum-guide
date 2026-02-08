"""
Configuration management for Museum Guide MVP.
Loads environment variables and provides centralized config access.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()


class Config:
    """Application configuration."""

    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    # ModelScope API Configuration
    MODELSCOPE_API_KEY: str = os.getenv(
        "MODELSCOPE_API_KEY",
        os.getenv("DASHSCOPE_API_KEY", "")
    )
    MODELSCOPE_API_BASE: str = os.getenv(
        "MODELSCOPE_API_BASE",
        "https://api-inference.modelscope.cn/v1"
    )

    ZHIPU_API_KEY: str = os.getenv("ZHIPU_API_KEY", "")
    ZHIPU_API_BASE: str = os.getenv(
        "ZHIPU_API_BASE",
        "https://open.bigmodel.cn/api/paas/v4"
    )

    # Recognition Settings
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.8"))
    CLIP_MODEL: str = os.getenv("CLIP_MODEL", "Qwen/Qwen3-Embedding-4B")
    VLM_MODEL: str = os.getenv("VLM_MODEL", "Qwen/Qwen2.5-VL-7B-Instruct")
    KIMI_VLM_MODEL: str = os.getenv("KIMI_VLM_MODEL", "moonshotai/Kimi-K2.5")
    NARRATION_MODEL: str = os.getenv("NARRATION_MODEL", "Qwen/Qwen3-32B")
    TEXT_EMBEDDING_MODEL: str = os.getenv("TEXT_EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-4B")
    TEXT_EMBEDDING_DIM: int = int(os.getenv("TEXT_EMBEDDING_DIM", "1536"))

    # TTS Settings
    TTS_PROFESSIONAL_VOICE: str = os.getenv("TTS_PROFESSIONAL_VOICE", "tongtong")
    TTS_CASUAL_VOICE: str = os.getenv("TTS_CASUAL_VOICE", "xiaochen")
    TTS_MODEL: str = os.getenv("TTS_MODEL", "glm-tts")

    # Storage Settings
    AUDIO_BUCKET: str = os.getenv("AUDIO_BUCKET", "audio-cache")

    @classmethod
    def validate(cls) -> list[str]:
        """Validate required configuration. Returns list of missing configs."""
        missing = []
        if not cls.SUPABASE_URL:
            missing.append("SUPABASE_URL")
        if not cls.SUPABASE_KEY:
            missing.append("SUPABASE_KEY")
        if not (cls.MODELSCOPE_API_KEY or cls.ZHIPU_API_KEY):
            missing.append("API_KEY")
        return missing


# Singleton instance
config = Config()
