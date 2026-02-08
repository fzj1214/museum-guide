#!/usr/bin/env python3
"""
Storage setup script for Supabase.
Creates the audio-cache bucket for storing TTS audio files.
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET_NAME = os.getenv("AUDIO_BUCKET", "audio-cache")


def setup_storage():
    """Create audio cache bucket in Supabase Storage."""
    if not all([SUPABASE_URL, SUPABASE_KEY]):
        print("Error: Missing SUPABASE_URL or SUPABASE_KEY")
        return

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    try:
        # Create bucket
        supabase.storage.create_bucket(
            BUCKET_NAME,
            options={
                "public": True,
                "file_size_limit": 10485760,  # 10MB
                "allowed_mime_types": ["audio/wav", "audio/mpeg", "audio/mp3"]
            }
        )
        print(f"Created bucket: {BUCKET_NAME}")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"Bucket {BUCKET_NAME} already exists")
        else:
            print(f"Error creating bucket: {e}")


if __name__ == "__main__":
    setup_storage()
