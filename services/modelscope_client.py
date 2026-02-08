"""
ModelScope API client wrapper.
"""

from typing import Any, Optional
import httpx

from config import config


class ModelScopeClient:
    """Client for ModelScope API inference."""

    def __init__(self):
        self.api_key = config.MODELSCOPE_API_KEY
        self.base_url = config.MODELSCOPE_API_BASE.rstrip("/")
        self.timeout = httpx.Timeout(60.0)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def _post_json(self, path: str, payload: dict) -> tuple[int, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}{path}",
                headers=self._headers(),
                json=payload
            )
        try:
            data = response.json()
        except Exception:
            data = {"error": response.text}
        return response.status_code, data

    async def chat_completions(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 512,
        enable_thinking: bool = False
    ) -> dict:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "enable_thinking": enable_thinking
        }
        status_code, data = await self._post_json(
            "/chat/completions",
            payload
        )
        return {
            "status_code": status_code,
            "data": data
        }

    async def embeddings(
        self,
        model: str,
        inputs: list[Any],
        dimensions: Optional[int] = None
    ) -> Optional[list]:
        payload = {
            "model": model,
            "input": inputs,
            "encoding_format": "float"
        }
        if dimensions:
            payload["dimensions"] = dimensions
        status_code, data = await self._post_json("/embeddings", payload)
        if status_code >= 400:
            return None
        if isinstance(data, dict):
            if "data" in data and data["data"]:
                return data["data"][0].get("embedding")
            output = data.get("output")
            if isinstance(output, dict):
                embeddings = output.get("embeddings")
                if embeddings:
                    return embeddings[0].get("embedding")
            embeddings = data.get("embeddings")
            if embeddings:
                return embeddings[0].get("embedding")
        return None

    async def audio_speech(
        self,
        model: str,
        text: str,
        voice: Optional[str] = None,
        response_format: str = "wav"
    ) -> Optional[bytes]:
        payload = {
            "model": model,
            "input": text,
            "response_format": response_format
        }
        if voice:
            payload["voice"] = voice
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/audio/speech",
                headers=self._headers(),
                json=payload
            )
        if response.status_code >= 400:
            return None
        return response.content


_client: Optional[ModelScopeClient] = None


def get_modelscope_client() -> ModelScopeClient:
    global _client
    if _client is None:
        _client = ModelScopeClient()
    return _client
