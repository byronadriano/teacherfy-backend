-- Content Cache Migration
-- This table stores generated content to avoid regeneration for identical inputs

CREATE TABLE IF NOT EXISTS content_cache (
    id SERIAL PRIMARY KEY,
    -- Cache key components
    resource_type VARCHAR(50) NOT NULL,
    lesson_topic VARCHAR(500) NOT NULL,
    subject_focus VARCHAR(100) NOT NULL,
    grade_level VARCHAR(50) NOT NULL,
    language VARCHAR(50) NOT NULL DEFAULT 'English',
    num_sections INTEGER DEFAULT 5,
    selected_standards TEXT[], -- Array of standards
    
    -- Cache key hash for fast lookups
    cache_key_hash VARCHAR(64) NOT NULL UNIQUE,
    
    -- Cached content
    structured_content JSONB NOT NULL,
    
    -- Metadata
    generation_count INTEGER DEFAULT 0, -- How many times this content was used
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Optional: Track original creator (for analytics)
    created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_content_cache_hash ON content_cache(cache_key_hash);
CREATE INDEX IF NOT EXISTS idx_content_cache_type ON content_cache(resource_type);
CREATE INDEX IF NOT EXISTS idx_content_cache_topic ON content_cache(lesson_topic);
CREATE INDEX IF NOT EXISTS idx_content_cache_created_at ON content_cache(created_at);
CREATE INDEX IF NOT EXISTS idx_content_cache_last_used ON content_cache(last_used_at);

-- Composite index for common queries
CREATE INDEX IF NOT EXISTS idx_content_cache_lookup ON content_cache(resource_type, subject_focus, grade_level);
