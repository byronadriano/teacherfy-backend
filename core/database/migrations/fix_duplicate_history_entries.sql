-- Migration: Fix duplicate history entries and prevent future duplicates
-- Date: 2024-01-XX
-- Description: Add unique constraints and cleanup duplicate entries in user_activities table

-- Step 1: Remove existing duplicates, keeping the most recent one
WITH duplicates AS (
    SELECT id,
           ROW_NUMBER() OVER (
             PARTITION BY user_id, 
                         COALESCE(lesson_data->>'lessonTopic', lesson_data->>'generatedTitle', 'Untitled'),
                         COALESCE(lesson_data->>'resourceType', 'PRESENTATION'),
                         DATE(created_at)
             ORDER BY created_at DESC
           ) as rn
    FROM user_activities
    WHERE lesson_data IS NOT NULL
)
DELETE FROM user_activities
WHERE id IN (
    SELECT id FROM duplicates WHERE rn > 1
);

-- Step 2: Add a computed column for unique content identification
ALTER TABLE user_activities 
ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64);

-- Step 3: Create a function to generate content hash
CREATE OR REPLACE FUNCTION generate_content_hash(lesson_data_json JSONB)
RETURNS VARCHAR(64) AS $$
BEGIN
    RETURN ENCODE(
        SHA256(
            CONCAT(
                COALESCE(lesson_data_json->>'lessonTopic', ''),
                '|',
                COALESCE(lesson_data_json->>'resourceType', 'PRESENTATION'),
                '|',
                COALESCE(lesson_data_json->>'subjectFocus', ''),
                '|',
                COALESCE(lesson_data_json->>'gradeLevel', '')
            )::BYTEA
        ), 
        'hex'
    );
END;
$$ LANGUAGE plpgsql;

-- Step 4: Update existing records with content hash
UPDATE user_activities 
SET content_hash = generate_content_hash(lesson_data)
WHERE lesson_data IS NOT NULL AND content_hash IS NULL;

-- Step 5: Add unique constraint to prevent duplicates within the same day
-- Note: Using ALTER TABLE ADD CONSTRAINT instead of CREATE UNIQUE INDEX for UPSERT compatibility
DO $$
BEGIN
    -- Drop old index if exists
    DROP INDEX IF EXISTS idx_unique_user_activity_daily;
    
    -- Add proper unique constraint (non-deferrable for ON CONFLICT support)
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'unique_user_activity_daily') THEN
        ALTER TABLE user_activities 
        ADD CONSTRAINT unique_user_activity_daily 
        UNIQUE (user_id, content_hash, activity_date);
    END IF;
END $$;

-- Step 6: Add index for performance
CREATE INDEX IF NOT EXISTS idx_user_activities_content_hash 
ON user_activities(content_hash) 
WHERE content_hash IS NOT NULL;

-- Step 7: Add trigger to automatically update content_hash on insert/update
CREATE OR REPLACE FUNCTION update_content_hash()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.lesson_data IS NOT NULL THEN
        NEW.content_hash := generate_content_hash(NEW.lesson_data);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_content_hash ON user_activities;
CREATE TRIGGER trigger_update_content_hash
    BEFORE INSERT OR UPDATE ON user_activities
    FOR EACH ROW EXECUTE FUNCTION update_content_hash();

-- Step 8: Add constraint to prevent null content_hash for lesson entries
ALTER TABLE user_activities 
ADD CONSTRAINT check_content_hash_not_null_for_lessons
CHECK (lesson_data IS NULL OR content_hash IS NOT NULL);

COMMIT;