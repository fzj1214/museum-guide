-- ============================================
-- 002: Create Tables
-- ============================================

-- Halls table: Museum exhibition halls
CREATE TABLE IF NOT EXISTS halls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hall_name TEXT NOT NULL,
    floor INTEGER NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index on floor for sorting
CREATE INDEX IF NOT EXISTS idx_halls_floor ON halls(floor);

-- Add comment
COMMENT ON TABLE halls IS 'Museum exhibition halls';


-- Artworks table: Art pieces with embeddings for vector search
CREATE TABLE IF NOT EXISTS artworks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name_cn TEXT NOT NULL,
    name_en TEXT,
    artist TEXT NOT NULL,
    year TEXT,
    style TEXT,
    hall_id UUID REFERENCES halls(id) ON DELETE SET NULL,
    image_url TEXT,
    embedding vector(1536),  -- CLIP embedding dimension
    description_professional TEXT,
    description_casual TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for vector similarity search (using ivfflat for better performance)
CREATE INDEX IF NOT EXISTS idx_artworks_embedding
ON artworks USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create index on hall_id for joins
CREATE INDEX IF NOT EXISTS idx_artworks_hall_id ON artworks(hall_id);

-- Add comment
COMMENT ON TABLE artworks IS 'Artwork catalog with vector embeddings for similarity search';


-- Audio cache table: Cached TTS audio files
CREATE TABLE IF NOT EXISTS audio_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artwork_id UUID NOT NULL REFERENCES artworks(id) ON DELETE CASCADE,
    style TEXT NOT NULL CHECK (style IN ('professional', 'casual')),
    voice TEXT NOT NULL,
    audio_url TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Ensure one audio per artwork-style combination
    UNIQUE(artwork_id, style)
);

-- Create index for quick lookup
CREATE INDEX IF NOT EXISTS idx_audio_cache_lookup
ON audio_cache(artwork_id, style);

-- Add comment
COMMENT ON TABLE audio_cache IS 'Cached TTS audio files for artworks';
