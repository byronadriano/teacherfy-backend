# core/database/database.py - FIXED VERSION with better error handling
import os
import sys
import json
import logging
import psycopg2
from contextlib import contextmanager
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

logger = logging.getLogger(__name__)

# Database configuration with environment variables
DB_CONFIG = {
    'dbname': os.environ.get('POSTGRES_DB', 'teacherfy_db'),
    'user': os.environ.get('POSTGRES_USER', 'bpulluta'),
    'password': os.environ.get('POSTGRES_PASSWORD', 'P!p!to031323!'),
    'host': os.environ.get('POSTGRES_HOST', 'teacherfydb.postgres.database.azure.com'),
    'port': os.environ.get('POSTGRES_PORT', '5432'),
    'sslmode': 'require'
}

@contextmanager
def get_db_connection():
    """Get a database connection with better error handling."""
    conn = None
    try:
        logger.debug(f"Attempting database connection to {DB_CONFIG['host']}")
        conn = psycopg2.connect(**DB_CONFIG)
        logger.debug("Database connection successful")
        yield conn
    except psycopg2.OperationalError as e:
        logger.error(f"Database connection failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected database error: {e}")
        raise
    finally:
        if conn is not None:
            conn.close()
            logger.debug("Database connection closed")

@contextmanager
def get_db_cursor(commit=False):
    """Get a database cursor with automatic commit option."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            yield cursor
            if commit:
                conn.commit()
                logger.debug("Database transaction committed")
        except Exception as e:
            conn.rollback()
            logger.error(f"Database operation error, rolled back: {e}")
            raise
        finally:
            cursor.close()

def get_user_by_email(email):
    """Get a user by email with better error handling."""
    if not email:
        logger.warning("get_user_by_email called with empty email")
        return None
        
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            result = cursor.fetchone()
            logger.debug(f"User lookup for {email}: {'found' if result else 'not found'}")
            return result
    except Exception as e:
        logger.error(f"Error getting user by email {email}: {e}")
        raise

def create_user(email, name, picture_url):
    """Create or update a user with comprehensive error handling."""
    logger.info(f"🔍 create_user called for email: {email}")
    
    if not email:
        raise ValueError("Email is required")
    
    if not name:
        name = email.split('@')[0]  # Use email prefix as fallback name
        
    try:
        with get_db_cursor(commit=True) as cursor:
            logger.debug(f"Executing user upsert for {email}")
            
            query = """
            INSERT INTO users (email, name, picture_url, created_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (email) DO UPDATE
              SET name = EXCLUDED.name,
                  picture_url = EXCLUDED.picture_url
            RETURNING id, email, name
            """
            
            cursor.execute(query, (email, name, picture_url))
            result = cursor.fetchone()
            
            if result:
                user_id = result['id']
                logger.info(f"✅ User created/updated successfully: ID={user_id}, email={email}")
                return user_id
            else:
                logger.error("❌ No result returned from user creation query")
                raise Exception("Failed to create/update user: no result returned")
                
    except psycopg2.IntegrityError as e:
        logger.error(f"❌ Database integrity error creating user {email}: {e}")
        raise
    except psycopg2.OperationalError as e:
        logger.error(f"❌ Database connection error creating user {email}: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error creating user {email}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise

def log_user_login(user_id):
    """Log a user login with better error handling."""
    if not user_id:
        logger.warning("log_user_login called with empty user_id")
        return False
        
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                "INSERT INTO user_logins (user_id, login_time) VALUES (%s, CURRENT_TIMESTAMP)", 
                (user_id,)
            )
            logger.debug(f"Login logged for user_id: {user_id}")
            return True
    except Exception as e:
        logger.error(f"Error logging user login for user_id {user_id}: {e}")
        # Don't raise - login logging failure shouldn't break authentication
        return False

def log_user_activity(user_id, activity, lesson_data=None):
    """Log a user activity with better error handling."""
    if not user_id or not activity:
        logger.warning(f"log_user_activity called with invalid params: user_id={user_id}, activity={activity}")
        return False
        
    try:
        with get_db_cursor(commit=True) as cursor:
            # Check if the table has 'activity_time' or 'created_at' column
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'user_activities' 
                AND column_name IN ('activity_time', 'created_at')
            """)
            time_columns = [row['column_name'] for row in cursor.fetchall()]
            
            time_column = 'activity_time' if 'activity_time' in time_columns else 'created_at'
            
            query = f"""
                INSERT INTO user_activities (user_id, activity, lesson_data, {time_column})
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            """
            
            cursor.execute(query, (user_id, activity, json.dumps(lesson_data) if lesson_data else None))
            logger.debug(f"Activity logged for user_id {user_id}: {activity}")
            return True
    except Exception as e:
        logger.error(f"Error logging user activity for user_id {user_id}: {e}")
        # Don't raise - activity logging failure shouldn't break the main flow
        return False

def get_example_outline(name):
    """Get an example outline by name."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT content FROM example_outlines WHERE name = %s", (name,))
            result = cursor.fetchone()
            return json.loads(result['content']) if result else None
    except Exception as e:
        logger.error(f"Error getting example outline {name}: {e}")
        return None

def save_example_outline(name, content):
    """Save or update an example outline."""
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """
                INSERT INTO example_outlines (name, content, created_at, updated_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (name) DO UPDATE
                  SET content = EXCLUDED.content,
                      updated_at = CURRENT_TIMESTAMP
                """,
                (name, json.dumps(content))
            )
            logger.debug(f"Example outline saved: {name}")
            return True
    except Exception as e:
        logger.error(f"Error saving example outline {name}: {e}")
        return False

def test_connection():
    """Test the database connection with detailed logging."""
    try:
        logger.debug("Testing database connection...")
        with get_db_cursor() as cursor:
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            if result and result['test'] == 1:
                logger.info("✅ Database connection test successful")
                return True
            else:
                logger.error("❌ Database connection test failed: unexpected result")
                return False
    except psycopg2.OperationalError as e:
        logger.error(f"❌ Database connection test failed (operational): {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Database connection test failed (unexpected): {e}")
        return False

def verify_database_schema():
    """Verify that all required tables exist."""
    required_tables = ['users', 'user_logins', 'user_activities', 'user_usage_limits']
    
    try:
        with get_db_cursor() as cursor:
            for table in required_tables:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    )
                """, (table,))
                exists = cursor.fetchone()['exists']
                logger.debug(f"Table {table}: {'exists' if exists else 'missing'}")
                if not exists:
                    logger.error(f"❌ Required table {table} is missing")
                    return False
            
            logger.info("✅ All required database tables exist")
            return True
    except Exception as e:
        logger.error(f"❌ Error verifying database schema: {e}")
        return False

# Initialize and verify database on import
if __name__ != "__main__":
    # Only run verification when imported, not when run directly
    try:
        if test_connection():
            verify_database_schema()
    except Exception as e:
        logger.error(f"Database initialization check failed: {e}")

def create_database_and_user():
    """Create the database and tables if they don't exist."""
    # This function remains the same but with better error handling
    try:
        # Connect to postgres database first
        admin_config = {
            'dbname': 'postgres',
            'user': os.environ.get('POSTGRES_ADMIN_USER', 'postgres'),
            'password': os.environ.get('POSTGRES_ADMIN_PASSWORD'),
            'host': DB_CONFIG['host'],
            'port': DB_CONFIG['port'],
            'sslmode': 'require'
        }
        
        logger.info("Creating database and tables...")
        
        with psycopg2.connect(**admin_config) as conn:
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            with conn.cursor() as cur:
                # Create database if it doesn't exist
                cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_CONFIG['dbname']}'")
                if not cur.fetchone():
                    cur.execute(f"CREATE DATABASE {DB_CONFIG['dbname']}")
                    logger.info(f"Database {DB_CONFIG['dbname']} created")
        
        # Now connect to the target database and create tables
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                # Read and execute schema
                schema_sql = """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    name VARCHAR(255),
                    picture_url TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS user_logins (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    login_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS user_activities (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    activity VARCHAR(255) NOT NULL,
                    lesson_data JSONB,
                    activity_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS user_usage_limits (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    ip_address VARCHAR(45) NOT NULL,
                    generations_used INTEGER DEFAULT 0,
                    downloads_used INTEGER DEFAULT 0,
                    last_reset TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                -- Create indexes
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                CREATE INDEX IF NOT EXISTS idx_user_logins_user_id ON user_logins(user_id);
                CREATE INDEX IF NOT EXISTS idx_user_activities_user_id ON user_activities(user_id);
                
                -- Unique constraints for usage limits
                CREATE UNIQUE INDEX IF NOT EXISTS idx_user_usage_limits_anonymous 
                  ON user_usage_limits(ip_address) WHERE user_id IS NULL;
                CREATE UNIQUE INDEX IF NOT EXISTS idx_user_usage_limits_registered 
                  ON user_usage_limits(user_id) WHERE user_id IS NOT NULL;
                """
                
                cur.execute(schema_sql)
                conn.commit()
                logger.info("✅ Database schema created/updated successfully")
                
    except Exception as e:
        logger.error(f"❌ Error creating database and tables: {e}")
        raise

if __name__ == "__main__":
    create_database_and_user()