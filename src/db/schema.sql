-- src/db/schema.sql

-- Users and Authentication
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    picture_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    tier_id INTEGER,
    generation_count INTEGER DEFAULT 0,
    download_count INTEGER DEFAULT 0
);

-- User Login History
CREATE TABLE IF NOT EXISTS user_logins (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    login_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User Activities
CREATE TABLE IF NOT EXISTS user_activities (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    activity VARCHAR(255) NOT NULL,
    lesson_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Example Outlines
CREATE TABLE IF NOT EXISTS example_outlines (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    content JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Anonymous Usage Tracking
CREATE TABLE IF NOT EXISTS anonymous_usage (
    id SERIAL PRIMARY KEY,
    ip_address VARCHAR(45) NOT NULL UNIQUE,
    generation_count INTEGER DEFAULT 0,
    download_count INTEGER DEFAULT 0,
    first_access TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_access TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User Tiers
CREATE TABLE IF NOT EXISTS user_tiers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    max_generations INTEGER NOT NULL,
    max_downloads INTEGER NOT NULL,
    is_default BOOLEAN DEFAULT false
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_user_activities_user_id ON user_activities(user_id);
CREATE INDEX IF NOT EXISTS idx_user_logins_user_id ON user_logins(user_id);
CREATE INDEX IF NOT EXISTS idx_anonymous_ip ON anonymous_usage(ip_address);
CREATE INDEX IF NOT EXISTS idx_user_tier ON users(tier_id);

-- Insert default tiers
INSERT INTO user_tiers (name, max_generations, max_downloads, is_default) 
VALUES 
    ('Free', 3, 1, true),
    ('Basic', 10, 5, false),
    ('Premium', 100, 50, false),
    ('Enterprise', -1, -1, false)  -- -1 means unlimited
ON CONFLICT DO NOTHING;