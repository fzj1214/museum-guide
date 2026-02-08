"""
Artwork recognition service using VLM + Text Embedding vector search.
"""

from typing import Optional
import json
import re
from PIL import Image

from config import config
from .supabase_client import get_supabase_client
from .modelscope_client import get_modelscope_client
from utils.image_utils import encode_image_base64


class ArtworkRecognitionService:
    """Service for recognizing artworks from images."""

    def __init__(self):
        """Initialize recognition service."""
        self.supabase = get_supabase_client()
        self.similarity_threshold = config.SIMILARITY_THRESHOLD
        self.modelscope = get_modelscope_client()

    async def recognize(self, image: Image.Image) -> dict:
        """
        Main recognition entry point.
        Uses VLM extraction + text embedding vector search.

        Args:
            image: PIL Image object

        Returns:
            dict with artwork info or error message
        """
        try:
            vlm_result = await self._vlm_recognition(image)
            result = vlm_result
            if not vlm_result.get("success"):
                kimi_result = await self._kimi_recognition(image)
                if kimi_result.get("success"):
                    result = kimi_result
                elif kimi_result.get("error"):
                    result = kimi_result
            else:
                artwork = vlm_result.get("artwork", {})
                if self._is_insufficient_artwork(artwork):
                    kimi_result = await self._kimi_recognition(image)
                    if kimi_result.get("success"):
                        result = kimi_result

            if not result.get("success"):
                return result

            embedding_text = self._build_embedding_text(result["artwork"])
            embedding = await self._extract_text_embedding(embedding_text)

            if embedding:
                results = await self.supabase.search_artwork_by_vector(
                    embedding,
                    threshold=self.similarity_threshold,
                    limit=1
                )

                if results and len(results) > 0:
                    artwork = results[0]
                    full_info = await self.supabase.get_artwork_with_hall(
                        artwork["id"]
                    )
                    if full_info:
                        return {
                            "success": True,
                            "source": "vector_search",
                            "similarity": artwork.get("similarity", 0),
                            "artwork": full_info
                        }

            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Recognition failed: {str(e)}"
            }

    async def _extract_text_embedding(self, text: str) -> Optional[list]:
        """
        Extract text embedding using ModelScope API.

        Args:
            text: Text to embed

        Returns:
            List of floats (embedding vector) or None
        """
        try:
            embedding = await self.modelscope.embeddings(
                model=config.TEXT_EMBEDDING_MODEL,
                inputs=[text],
                dimensions=config.TEXT_EMBEDDING_DIM
            )
            return embedding

        except Exception as e:
            print(f"Embedding extraction error: {e}")
            return None

    def _build_embedding_text(self, artwork: dict) -> str:
        parts = []
        name_cn = artwork.get("name_cn")
        name_en = artwork.get("name_en")
        artist = artwork.get("artist")
        year = artwork.get("year")
        style = artwork.get("style")
        description = artwork.get("description_casual") or artwork.get("description_professional")

        if name_cn:
            parts.append(f"名称:{name_cn}")
        if name_en:
            parts.append(f"英文名:{name_en}")
        if artist:
            parts.append(f"作者:{artist}")
        if year:
            parts.append(f"年代:{year}")
        if style:
            parts.append(f"风格:{style}")
        if description:
            parts.append(f"描述:{description}")

        return "\n".join(parts)

    def _is_insufficient_artwork(self, artwork: dict) -> bool:
        name = (artwork.get("name_cn") or "").strip()
        artist = (artwork.get("artist") or "").strip()
        description = (
            artwork.get("description_casual")
            or artwork.get("description_professional")
            or ""
        ).strip()

        unknown_values = {"", "unknown", "未知", "不详", "none", "null"}
        name_unknown = name.lower() in unknown_values
        artist_unknown = artist.lower() in unknown_values
        description_empty = not description

        if name_unknown and artist_unknown:
            return True
        if name_unknown and description_empty:
            return True
        if artist_unknown and description_empty:
            return True
        return False

    def _parse_vlm_json(self, content: str) -> Optional[dict]:
        if not content:
            return None
        cleaned = content.strip()
        fence_match = re.search(
            r"```(?:json)?\s*([\s\S]*?)\s*```",
            cleaned,
            re.IGNORECASE
        )
        if fence_match:
            cleaned = fence_match.group(1).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        brace_match = re.search(r"\{[\s\S]*\}", cleaned)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                return None
        return None

    async def _vlm_recognition(self, image: Image.Image) -> dict:
        """
        Use Qwen-VL for real-time artwork recognition.

        Args:
            image: PIL Image object

        Returns:
            dict with recognition results
        """
        try:
            # Convert image to base64
            image_base64 = encode_image_base64(image)

            # Prepare messages for VLM
            messages = [{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": """请分析这张艺术品图片，并以JSON格式返回以下信息：
{
    "name_cn": "艺术品中文名称",
    "name_en": "艺术品英文名称（如果知道）",
    "artist": "作者",
    "year": "创作年代（如：1503-1519）",
    "style": "艺术流派（如：文艺复兴、印象派等）",
    "description": "简短描述（50字以内）"
}

如果无法识别为艺术品，请返回：
{"error": "无法识别为艺术品"}

只返回JSON，不要其他内容。"""
                    }
                ]
            }]

            response = await self.modelscope.chat_completions(
                model=config.VLM_MODEL,
                messages=messages,
                temperature=0.2,
                max_tokens=800,
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
                    content = "\n".join(parts)
                result = self._parse_vlm_json(content)
                if not isinstance(result, dict):
                    return {
                        "success": False,
                        "source": "vlm",
                        "error": "Failed to parse VLM response"
                    }
                if "error" in result:
                    return {
                        "success": False,
                        "source": "vlm",
                        "error": result["error"]
                    }
                return {
                    "success": True,
                    "source": "vlm",
                    "artwork": {
                        "id": None,
                        "name_cn": result.get("name_cn", "Unknown"),
                        "name_en": result.get("name_en", ""),
                        "artist": result.get("artist", "Unknown"),
                        "year": result.get("year", ""),
                        "style": result.get("style", ""),
                        "description_professional": None,
                        "description_casual": result.get("description", ""),
                        "halls": None
                    }
                }
            else:
                return {
                    "success": False,
                    "source": "vlm",
                    "error": f"VLM call failed: {response.get('data')}"
                }

        except Exception as e:
            return {
                "success": False,
                "source": "vlm",
                "error": f"VLM recognition error: {str(e)}"
            }

    async def _kimi_recognition(self, image: Image.Image) -> dict:
        try:
            image_base64 = encode_image_base64(image)

            messages = [{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": """请分析这张艺术品图片，并以JSON格式返回以下信息：
{
    "name_cn": "艺术品中文名称",
    "name_en": "艺术品英文名称（如果知道）",
    "artist": "作者",
    "year": "创作年代（如：1503-1519）",
    "style": "艺术流派（如：文艺复兴、印象派等）",
    "description": "简短描述（50字以内）"
}

如果无法识别为艺术品，请返回：
{"error": "无法识别为艺术品"}

只返回JSON，不要其他内容。"""
                    }
                ]
            }]

            response = await self.modelscope.chat_completions(
                model=config.KIMI_VLM_MODEL,
                messages=messages,
                temperature=0.2,
                max_tokens=800,
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
                    content = "\n".join(parts)
                result = self._parse_vlm_json(content)
                if not isinstance(result, dict):
                    return {
                        "success": False,
                        "source": "kimi",
                        "error": "Failed to parse Kimi response"
                    }
                if "error" in result:
                    return {
                        "success": False,
                        "source": "kimi",
                        "error": result["error"]
                    }
                return {
                    "success": True,
                    "source": "kimi",
                    "artwork": {
                        "id": None,
                        "name_cn": result.get("name_cn", "Unknown"),
                        "name_en": result.get("name_en", ""),
                        "artist": result.get("artist", "Unknown"),
                        "year": result.get("year", ""),
                        "style": result.get("style", ""),
                        "description_professional": None,
                        "description_casual": result.get("description", ""),
                        "halls": None
                    }
                }
            else:
                return {
                    "success": False,
                    "source": "kimi",
                    "error": f"Kimi call failed: {response.get('data')}"
                }

        except Exception as e:
            return {
                "success": False,
                "source": "kimi",
                "error": f"Kimi recognition error: {str(e)}"
            }


# Singleton instance
_service: Optional[ArtworkRecognitionService] = None


def get_recognition_service() -> ArtworkRecognitionService:
    """Get or create recognition service singleton."""
    global _service
    if _service is None:
        _service = ArtworkRecognitionService()
    return _service
