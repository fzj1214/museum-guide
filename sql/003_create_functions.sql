-- ============================================
-- 003: Create RPC Functions
-- ============================================

-- Vector similarity search function
-- Finds artworks matching the query embedding above a threshold
CREATE OR REPLACE FUNCTION match_artwork(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.8,
    match_count int DEFAULT 1
)
RETURNS TABLE (
    id uuid,
    name_cn text,
    artist text,
    hall_id uuid,
    similarity float
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        artworks.id,
        artworks.name_cn,
        artworks.artist,
        artworks.hall_id,
        (1 - (artworks.embedding <=> query_embedding))::float as similarity
    FROM artworks
    WHERE artworks.embedding IS NOT NULL
      AND (1 - (artworks.embedding <=> query_embedding)) > match_threshold
    ORDER BY artworks.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Add comment
COMMENT ON FUNCTION match_artwork IS 'Find artworks by vector similarity search';


-- Get artwork with hall information
CREATE OR REPLACE FUNCTION get_artwork_with_hall(artwork_id uuid)
RETURNS TABLE (
    id uuid,
    name_cn text,
    name_en text,
    artist text,
    year text,
    style text,
    image_url text,
    description_professional text,
    description_casual text,
    hall_id uuid,
    hall_name text,
    hall_floor integer,
    hall_description text
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.id,
        a.name_cn,
        a.name_en,
        a.artist,
        a.year,
        a.style,
        a.image_url,
        a.description_professional,
        a.description_casual,
        h.id as hall_id,
        h.hall_name,
        h.floor as hall_floor,
        h.description as hall_description
    FROM artworks a
    LEFT JOIN halls h ON a.hall_id = h.id
    WHERE a.id = artwork_id;
END;
$$;

-- Add comment
COMMENT ON FUNCTION get_artwork_with_hall IS 'Get artwork details with hall information';
