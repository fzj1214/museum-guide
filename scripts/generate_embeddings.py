#!/usr/bin/env python3
"""
Setup script for generating text embeddings for artworks.
Run this after setting up the database and inserting artwork records.
"""

import os
import asyncio

from supabase import create_client
import httpx

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MODELSCOPE_API_KEY = os.getenv("MODELSCOPE_API_KEY", os.getenv("DASHSCOPE_API_KEY", ""))
MODELSCOPE_API_BASE = os.getenv("MODELSCOPE_API_BASE", "https://api-inference.modelscope.cn/v1")
TEXT_EMBEDDING_MODEL = os.getenv("TEXT_EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-4B")
TEXT_EMBEDDING_DIM = int(os.getenv("TEXT_EMBEDDING_DIM", "1536"))


def build_artwork_text(artwork: dict) -> str:
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


async def get_embedding_from_text(text: str) -> list:
    """Get text embedding using ModelScope API."""
    headers = {
        "Authorization": f"Bearer {MODELSCOPE_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": TEXT_EMBEDDING_MODEL,
        "input": [text],
        "encoding_format": "float",
        "dimensions": TEXT_EMBEDDING_DIM
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{MODELSCOPE_API_BASE.rstrip('/')}/embeddings",
            headers=headers,
            json=payload
        )
    if resp.status_code == 200:
        data = resp.json()
        output = data.get("output") or data
        embeddings = output.get("embeddings") or output.get("data")
        if isinstance(embeddings, list) and embeddings:
            first = embeddings[0]
            if isinstance(first, dict):
                return first.get("embedding")
            return first
    else:
        try:
            print(f"Error getting embedding: {resp.json()}")
        except Exception:
            print(f"Error getting embedding: {resp.text}")
    return None


def update_artwork_embedding(supabase, artwork_id: str, embedding: list):
    """Update artwork record with embedding."""
    response = supabase.table("artworks").update({
        "embedding": embedding
    }).eq("id", artwork_id).execute()

    return response.data


async def main():
    """Main function to generate embeddings for all artworks."""
    if not all([SUPABASE_URL, SUPABASE_KEY, MODELSCOPE_API_KEY]):
        print("Error: Missing required environment variables.")
        print("Please set SUPABASE_URL, SUPABASE_KEY, and MODELSCOPE_API_KEY")
        return

    # Initialize Supabase client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Get all artworks without embeddings
    response = supabase.table("artworks").select(
        "id, name_cn, name_en, artist, year, style, description_professional, description_casual"
    ).is_("embedding", "null").execute()

    artworks = response.data
    print(f"Found {len(artworks)} artworks without embeddings")

    for artwork in artworks:
        print(f"Processing: {artwork['name_cn']}")

        embedding_text = build_artwork_text(artwork)
        if not embedding_text.strip():
            print(f"  Skipping - no metadata")
            continue

        embedding = await get_embedding_from_text(embedding_text)

        if embedding:
            update_artwork_embedding(supabase, artwork["id"], embedding)
            print(f"  Updated embedding ({len(embedding)} dimensions)")
        else:
            print(f"  Failed to get embedding")

    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
