#!/bin/bash
# run_migration.sh

# Make sure we're in the correct directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Create the migrations directory structure if it doesn't exist
echo "Setting up migration directory structure..."
mkdir -p src/db/migrations

# Copy migration script to the directory
echo "Creating migration script..."
cat > src/db/migrations/add_history_support.py << 'EOL'
# src/db/migrations/add_history_support.py
import psycopg2
import os
import sys
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_migration():
    """Run the migration to add history support to the database."""
    # Load environment variables
    load_dotenv()
    
    # Get database connection info from environment variables only
    dbname = os.getenv('POSTGRES_DB')
    user = os.getenv('POSTGRES_USER')
    password = os.getenv('POSTGRES_PASSWORD')
    host = os.getenv('POSTGRES_HOST')
    port = os.getenv('POSTGRES_PORT', '5432')
    
    # Ensure we have all required connection details
    if not all([dbname, user, password, host]):
        logger.error("Missing required database connection details in environment variables")
        sys.exit(1)
    
    # Connect to the database
    try:
        # For Azure PostgreSQL, we need to specify sslmode
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port,
            sslmode='require'  # Required for Azure PostgreSQL
        )
        conn.autocommit = True
        cursor = conn.cursor()
        logger.info(f"Connected to database {dbname} on host {host}")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        sys.exit(1)
    
    try:
        # First, check the table structure
        logger.info("Checking database structure...")
        
        # Check if the user_activities table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'user_activities'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            # Create the complete table
            logger.info("Creating user_activities table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_activities (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    activity VARCHAR(255) NOT NULL,
                    lesson_data JSONB,
                    activity_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            logger.info("user_activities table created successfully.")
        
        # Get existing columns
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'user_activities';
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        logger.info(f"Existing columns: {existing_columns}")
        
        # Check and add lesson_data column if it doesn't exist
        if 'lesson_data' not in existing_columns:
            logger.info("Adding lesson_data column...")
            cursor.execute("""
                ALTER TABLE user_activities
                ADD COLUMN lesson_data JSONB;
            """)
            logger.info("lesson_data column added successfully.")
        
        # Check for timestamp column
        has_activity_time = 'activity_time' in existing_columns
        has_created_at = 'created_at' in existing_columns
        
        # Add appropriate timestamp column if none exists
        if not has_activity_time and not has_created_at:
            logger.info("Adding timestamp column...")
            cursor.execute("""
                ALTER TABLE user_activities
                ADD COLUMN activity_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
            """)
            has_activity_time = True
            logger.info("activity_time column added successfully.")
        
        # Create necessary indexes
        logger.info("Creating indexes...")
        
        # Index on user_id
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_activities_user_id 
            ON user_activities(user_id);
        """)
        
        # Index on the appropriate timestamp column
        if has_activity_time:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_activities_activity_time 
                ON user_activities(activity_time);
            """)
        elif has_created_at:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_activities_created_at 
                ON user_activities(created_at);
            """)
        
        logger.info("Required indexes created successfully.")
        
        # Check if table has any data
        cursor.execute("SELECT COUNT(*) FROM user_activities;")
        count = cursor.fetchone()[0]
        
        # Add sample data if needed
        if count == 0:
            logger.info("Table is empty. Adding sample history data...")
            
            # First make sure we have at least one user
            cursor.execute("SELECT id FROM users LIMIT 1;")
            user_row = cursor.fetchone()
            
            if user_row:
                user_id = user_row[0]
                
                # Determine which timestamp column to use
                timestamp_col = 'activity_time' if has_activity_time else 'created_at'
                
                # Add sample history entries
                insert_query = f"""
                    INSERT INTO user_activities (user_id, activity, lesson_data, {timestamp_col})
                    VALUES 
                        (%s, 'Created PRESENTATION', %s, NOW() - INTERVAL '1 day'),
                        (%s, 'Created PRESENTATION', %s, NOW() - INTERVAL '2 days'),
                        (%s, 'Created LESSON_PLAN', %s, NOW() - INTERVAL '3 days');
                """
                
                # Sample lesson data as JSON strings
                sample_data_1 = '{"resourceType": "PRESENTATION", "lessonTopic": "Equivalent Fractions", "gradeLevel": "4th grade", "subjectFocus": "Math"}'
                sample_data_2 = '{"resourceType": "PRESENTATION", "lessonTopic": "Adding Mixed Fractions", "gradeLevel": "5th grade", "subjectFocus": "Math"}'
                sample_data_3 = '{"resourceType": "LESSON_PLAN", "lessonTopic": "Fractions Introduction", "gradeLevel": "3rd grade", "subjectFocus": "Math"}'
                
                cursor.execute(insert_query, (
                    user_id, sample_data_1,
                    user_id, sample_data_2,
                    user_id, sample_data_3
                ))
                
                logger.info("Sample history data added successfully.")
            else:
                logger.warning("No users found, skipping sample data creation.")
        
        logger.info("Migration completed successfully.")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_migration()
EOL

# Create __init__.py files
echo "Creating __init__.py files..."
touch src/db/migrations/__init__.py

# Run the migration
echo "Running database migration..."
python -m src.db.migrations.add_history_support

# Check if the migration was successful
if [ $? -eq 0 ]; then
    echo "✅ Migration completed successfully!"
else
    echo "❌ Migration failed!"
    exit 1
fi

# Start the application if specified
if [ "$1" == "--start" ]; then
    echo "Starting application..."
    python run_dev.py
fi