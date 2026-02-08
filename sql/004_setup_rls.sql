-- ============================================
-- 004: Set up Row Level Security (RLS)
-- ============================================

-- Enable RLS on all tables
ALTER TABLE halls ENABLE ROW LEVEL SECURITY;
ALTER TABLE artworks ENABLE ROW LEVEL SECURITY;
ALTER TABLE audio_cache ENABLE ROW LEVEL SECURITY;

-- Create policies for public read access (anonymous users can read)

-- Halls: Public read access
CREATE POLICY "Allow public read access on halls"
ON halls FOR SELECT
TO anon, authenticated
USING (true);

-- Artworks: Public read access
CREATE POLICY "Allow public read access on artworks"
ON artworks FOR SELECT
TO anon, authenticated
USING (true);

-- Audio cache: Public read access
CREATE POLICY "Allow public read access on audio_cache"
ON audio_cache FOR SELECT
TO anon, authenticated
USING (true);

-- Audio cache: Allow insert for authenticated service role
CREATE POLICY "Allow service role insert on audio_cache"
ON audio_cache FOR INSERT
TO authenticated
WITH CHECK (true);

-- Note: For production, you should create more restrictive policies
-- and use service role key for write operations
