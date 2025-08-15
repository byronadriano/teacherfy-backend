-- Production optimization: Add cleanup job for old cache entries
-- Run this periodically (daily/weekly) to prevent unbounded growth

-- Add cleanup function
CREATE OR REPLACE FUNCTION cleanup_old_cache_entries()
RETURNS TABLE(deleted_count INTEGER) AS $$
BEGIN
    -- Delete entries older than 30 days that haven't been used recently
    DELETE FROM content_cache 
    WHERE created_at < NOW() - INTERVAL '30 days' 
      AND last_used_at < NOW() - INTERVAL '7 days'
      AND generation_count <= 2; -- Only delete rarely used entries
    
    -- Return count of deleted rows
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- Add index for cleanup queries
CREATE INDEX IF NOT EXISTS idx_content_cache_cleanup 
    ON content_cache(created_at, last_used_at, generation_count);

-- Add comment
COMMENT ON FUNCTION cleanup_old_cache_entries() IS 'Cleanup old, rarely used cache entries to prevent unbounded growth';
