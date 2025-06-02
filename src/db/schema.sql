-- src/db/schema.sql - UPDATED with subscription tracking

-- Users and Authentication
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    picture_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    tier_id INTEGER,
    generation_count INTEGER DEFAULT 0,
    download_count INTEGER DEFAULT 0,
    -- ADDED: Subscription fields
    subscription_tier VARCHAR(50) DEFAULT 'free',
    subscription_status VARCHAR(50) DEFAULT 'inactive',
    subscription_start_date TIMESTAMP WITH TIME ZONE,
    subscription_end_date TIMESTAMP WITH TIME ZONE,
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255)
);

-- User Login History
CREATE TABLE IF NOT EXISTS user_logins (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    login_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User Activities (updated to store lesson data)
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

-- User Usage Limits (UPDATED with hourly tracking)
CREATE TABLE IF NOT EXISTS user_usage_limits (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    ip_address VARCHAR(45) NOT NULL,
    generations_used INTEGER DEFAULT 0,
    downloads_used INTEGER DEFAULT 0,
    last_reset TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- ADDED: Hourly tracking fields
    hourly_generations INTEGER DEFAULT 0,
    last_hourly_reset TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ADDED: Subscription history table
CREATE TABLE IF NOT EXISTS user_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    subscription_tier VARCHAR(50) NOT NULL,
    subscription_status VARCHAR(50) NOT NULL,
    stripe_subscription_id VARCHAR(255),
    stripe_customer_id VARCHAR(255),
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_user_activities_user_id ON user_activities(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activities_created_at ON user_activities(created_at);
CREATE INDEX IF NOT EXISTS idx_user_logins_user_id ON user_logins(user_id);
CREATE INDEX IF NOT EXISTS idx_anonymous_ip ON anonymous_usage(ip_address);
CREATE INDEX IF NOT EXISTS idx_user_tier ON users(tier_id);
CREATE INDEX IF NOT EXISTS idx_user_subscription_tier ON users(subscription_tier);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_email ON user_subscriptions(email);

-- Create partial unique indexes
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_usage_limits_anonymous 
  ON user_usage_limits(ip_address)
  WHERE user_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_usage_limits_registered 
  ON user_usage_limits(user_id)
  WHERE user_id IS NOT NULL;

-- Insert default tiers if they don't exist
INSERT INTO user_tiers (name, max_generations, max_downloads, is_default) 
VALUES 
    ('Free', 10, 10, true),      -- UPDATED: 10 generations per month
    ('Premium', -1, -1, false)   -- UPDATED: Unlimited for premium
ON CONFLICT DO NOTHING;

-- Update existing free users to have proper subscription status
UPDATE users 
SET subscription_tier = 'free', subscription_status = 'active' 
WHERE subscription_tier IS NULL OR subscription_tier = '';

-- Update existing premium users (if any exist with tier_id = 2 or 3)
UPDATE users 
SET subscription_tier = 'premium', subscription_status = 'active' 
WHERE tier_id IN (2, 3, 4); -- Basic, Premium, Enterprise tiers