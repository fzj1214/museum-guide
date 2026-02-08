"""
Text-to-Speech service using ZhipuAI GLM-TTS API.
Supports audio caching in Supabase Storage.
"""
from typing import Optional, Tuple
import httpx
from config import config
from .supabase_client import get_supabase_client


class TTSService:
    """Service for text-to-speech synthesis."""

    VOICE_MAP = {
        "professional": "tongtong",
        "casual": "xiaochen"
    }

    def __init__(self):
        """Initialize TTS service."""
        self.supabase = get_supabase_client()
        self.timeout = httpx.Timeout(60.0)

    async def synthesize(
        self,
        text: str,
        artwork_id: str,
        style: str
    ) -> dict:
        """
        Synthesize speech from text with caching.

        Args:
            text: Text to synthesize
            artwork_id: Artwork ID for caching
            style: Voice style ("professional" or "casual")

        Returns:
            dict with audio_url, audio_data or error
        """
        try:
            # 1. Check cache first
            cached_url = await self._get_cached_audio(artwork_id, style)
            if cached_url:
                cached_audio = await self._download_audio(cached_url)
                if not cached_audio:
                    return {
                        "success": False,
                        "error": "缓存音频下载失败"
                    }
                return {
                    "success": True,
                    "source": "cached",
                    "audio_url": cached_url,
                    "audio_data": cached_audio
                }

            # 2. Synthesize new audio
            voice = self.VOICE_MAP.get(style, "tongtong")
            audio_data, error = await self._call_sambert(text, voice)

            if not audio_data:
                return {
                    "success": False,
                    "error": error or "TTS synthesis failed"
                }

            # 3. Upload to storage
            audio_url = await self._upload_to_storage(
                audio_data, artwork_id, style
            )

            # 4. Save cache record
            await self._save_cache_record(artwork_id, style, voice, audio_url)

            return {
                "success": True,
                "source": "generated",
                "audio_url": audio_url,
                "audio_data": audio_data
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"TTS error: {str(e)}"
            }

    async def synthesize_direct(
        self,
        text: str,
        style: str = "professional"
    ) -> Optional[bytes]:
        """
        Synthesize speech without caching (for VLM results).

        Args:
            text: Text to synthesize
            style: Voice style

        Returns:
            Audio bytes or None
        """
        voice = self.VOICE_MAP.get(style, "tongtong")
        audio_data, _ = await self._call_sambert(text, voice)
        return audio_data

    async def _call_sambert(
        self,
        text: str,
        voice: str
    ) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Call ZhipuAI GLM-TTS API.

        Args:
            text: Text to synthesize
            voice: Voice ID

        Returns:
            Audio bytes or None
        """
        try:
            if not config.ZHIPU_API_KEY:
                return None, "缺少 ZHIPU_API_KEY"
            model = config.TTS_MODEL or "glm-tts"
            payload = {
                "model": model,
                "input": text,
                "voice": voice,
                "response_format": "wav"
            }
            headers = {
                "Authorization": f"Bearer {config.ZHIPU_API_KEY}",
                "Content-Type": "application/json"
            }
            url = f"{config.ZHIPU_API_BASE.rstrip('/')}/audio/speech"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
            if response.status_code >= 400:
                return None, self._format_error(response)
            if "application/json" in response.headers.get("content-type", ""):
                return None, self._format_error(response)
            return response.content, None

        except Exception as e:
            print(f"Sambert TTS error: {e}")
            return None, str(e)

    async def _get_cached_audio(
        self,
        artwork_id: str,
        style: str
    ) -> Optional[str]:
        """Get cached audio URL from database."""
        return await self.supabase.get_cached_audio(artwork_id, style)

    async def _upload_to_storage(
        self,
        audio_data: bytes,
        artwork_id: str,
        style: str
    ) -> str:
        """Upload audio to Supabase Storage."""
        # Generate unique filename
        filename = f"{artwork_id}_{style}.wav"
        return await self.supabase.upload_audio(filename, audio_data)

    async def _download_audio(self, audio_url: str) -> Optional[bytes]:
        if not audio_url or not audio_url.startswith("http"):
            return None
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(audio_url)
            if response.status_code >= 400:
                return None
            return response.content
        except Exception:
            return None

    def _format_error(self, response: httpx.Response) -> str:
        try:
            data = response.json()
            if isinstance(data, dict):
                error = data.get("error")
                if isinstance(error, dict):
                    return error.get("message") or str(error)
                return data.get("message") or str(data)
            return str(data)
        except Exception:
            return response.text[:200]

    async def _save_cache_record(
        self,
        artwork_id: str,
        style: str,
        voice: str,
        audio_url: str
    ):
        """Save audio cache record to database."""
        await self.supabase.save_audio_cache(
            artwork_id, style, voice, audio_url
        )


# Singleton instance
_service: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """Get or create TTS service singleton."""
    global _service
    if _service is None:
        _service = TTSService()
    return _service
