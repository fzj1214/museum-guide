"""
Supabase client wrapper for Museum Guide MVP.
Provides database operations and storage access.
"""

from typing import Optional
from supabase import create_client, Client
from config import config


class SupabaseClient:
    """Wrapper class for Supabase operations."""

    def __init__(self):
        """Initialize Supabase client."""
        self.client: Client = create_client(
            config.SUPABASE_URL,
            config.SUPABASE_KEY
        )

    # ==================== Artwork Operations ====================

    async def get_artwork_by_id(self, artwork_id: str) -> Optional[dict]:
        """Get artwork by ID with hall information."""
        response = self.client.table("artworks").select(
            "*, halls(hall_name, floor, description)"
        ).eq("id", artwork_id).single().execute()
        return response.data if response.data else None

    async def search_artwork_by_vector(
        self,
        embedding: list[float],
        threshold: float = 0.8,
        limit: int = 1
    ) -> list[dict]:
        """Search artwork using vector similarity."""
        response = self.client.rpc(
            "match_artwork",
            {
                "query_embedding": embedding,
                "match_threshold": threshold,
                "match_count": limit
            }
        ).execute()
        return response.data if response.data else []

    async def get_artwork_with_hall(self, artwork_id: str) -> Optional[dict]:
        """Get artwork with its hall information."""
        response = self.client.table("artworks").select(
            "id, name_cn, name_en, artist, year, style, image_url, "
            "description_professional, description_casual, "
            "halls(id, hall_name, floor, description)"
        ).eq("id", artwork_id).single().execute()
        return response.data if response.data else None

    # ==================== Hall Operations ====================

    async def get_hall_by_id(self, hall_id: str) -> Optional[dict]:
        """Get hall by ID."""
        response = self.client.table("halls").select("*").eq(
            "id", hall_id
        ).single().execute()
        return response.data if response.data else None

    async def list_halls(self) -> list[dict]:
        """List all halls."""
        response = self.client.table("halls").select("*").order(
            "floor", desc=False
        ).execute()
        return response.data if response.data else []

    # ==================== Audio Cache Operations ====================

    async def get_cached_audio(
        self,
        artwork_id: str,
        style: str
    ) -> Optional[str]:
        """Get cached audio URL for artwork and style."""
        try:
            response = self.client.table("audio_cache").select("audio_url").eq(
                "artwork_id", artwork_id
            ).eq("style", style).single().execute()
            return response.data["audio_url"] if response.data else None
        except Exception as e:
            if "PGRST116" in str(e):
                return None
            raise

    async def save_audio_cache(
        self,
        artwork_id: str,
        style: str,
        voice: str,
        audio_url: str
    ) -> dict:
        """Save audio cache record."""
        response = self.client.table("audio_cache").insert({
            "artwork_id": artwork_id,
            "style": style,
            "voice": voice,
            "audio_url": audio_url
        }).execute()
        return response.data[0] if response.data else {}

    # ==================== Storage Operations ====================

    async def upload_audio(
        self,
        file_path: str,
        file_data: bytes
    ) -> str:
        """Upload audio file to Supabase Storage."""
        bucket = self.client.storage.from_(config.AUDIO_BUCKET)
        bucket.upload(file_path, file_data, {"content-type": "audio/wav"})
        return bucket.get_public_url(file_path)

    async def get_audio_url(self, file_path: str) -> str:
        """Get public URL for audio file."""
        bucket = self.client.storage.from_(config.AUDIO_BUCKET)
        return bucket.get_public_url(file_path)


# Singleton instance
_client: Optional[SupabaseClient] = None


def get_supabase_client() -> SupabaseClient:
    """Get or create Supabase client singleton."""
    global _client
    if _client is None:
        _client = SupabaseClient()
    return _client
