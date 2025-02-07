# src/db/database.py
import os
import sys
import json
import logging
import psycopg2
from contextlib import contextmanager
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

logger = logging.getLogger(__name__)

# Database configuration (with defaults)
DB_CONFIG = {
    'dbname': os.getenv('POSTGRES_DB', 'teacherfy_db'),
    'user': os.getenv('POSTGRES_USER', 'teacherfy_user'),
    'password': os.getenv('POSTGRES_PASSWORD', '132392'),
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5432')
}

@contextmanager
def get_db_connection():
    """Get a database connection."""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        yield conn
    except Exception as e:
        logger.error("Database connection error", exc_info=True)
        raise
    finally:
        if conn is not None:
            conn.close()

@contextmanager
def get_db_cursor(commit=False):
    """Get a database cursor with automatic commit option."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            yield cursor
            if commit:
                conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error("Database operation error", exc_info=True)
            raise
        finally:
            cursor.close()

def get_user_by_email(email):
    """Get a user by email."""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        return cursor.fetchone()

def create_user(email, name, picture_url):
    """Create or update a user."""
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(
            """
            INSERT INTO users (email, name, picture_url)
            VALUES (%s, %s, %s)
            ON CONFLICT (email) DO UPDATE
              SET name = EXCLUDED.name,
                  picture_url = EXCLUDED.picture_url
            RETURNING id
            """,
            (email, name, picture_url)
        )
        return cursor.fetchone()['id']

def log_user_login(user_id):
    """Log a user login."""
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("INSERT INTO user_logins (user_id) VALUES (%s)", (user_id,))

def log_user_activity(user_id, activity, lesson_data=None):
    """Log a user activity."""
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(
            """
            INSERT INTO user_activities (user_id, activity, lesson_data)
            VALUES (%s, %s, %s)
            """,
            (user_id, activity, json.dumps(lesson_data) if lesson_data else None)
        )

def get_example_outline(name):
    """Get an example outline by name."""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT content FROM example_outlines WHERE name = %s", (name,))
        result = cursor.fetchone()
        return json.loads(result['content']) if result else None

def save_example_outline(name, content):
    """Save or update an example outline."""
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(
            """
            INSERT INTO example_outlines (name, content)
            VALUES (%s, %s)
            ON CONFLICT (name) DO UPDATE
              SET content = EXCLUDED.content,
                  updated_at = CURRENT_TIMESTAMP
            """,
            (name, json.dumps(content))
        )

def test_connection():
    """Test the database connection."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT 1")
            logger.info("Database connection successful")
            return True
    except Exception as e:
        logger.error("Database connection test failed", exc_info=True)
        return False

def create_database_and_user():
    """
    Create the database, tables, indexes, and application user.
    This function drops existing tables and re-creates them.
    """
    # Default connection parameters for the admin user
    conn_params = {
        'dbname': 'postgres',
        'user': os.getenv('POSTGRES_ADMIN_USER', 'postgres'),
        'password': os.getenv('POSTGRES_ADMIN_PASSWORD', ''),
        'host': os.getenv('POSTGRES_HOST', 'localhost')
    }

    try:
        # Connect as admin
        conn = psycopg2.connect(**conn_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        # Application database and user parameters
        DB_NAME = os.getenv('POSTGRES_DB', 'teacherfy_db')
        DB_USER = os.getenv('POSTGRES_USER', 'teacherfy_user')
        DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', '132392')

        # Create the database if it doesn't already exist
        cur.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{DB_NAME}'")
        if not cur.fetchone():
            cur.execute(f'CREATE DATABASE {DB_NAME}')
            print(f"Database {DB_NAME} created successfully")

        # Connect to the new database to create tables and indexes
        conn_new_db = psycopg2.connect(
            dbname=DB_NAME,
            user=conn_params['user'],
            password=conn_params['password'],
            host=conn_params['host']
        )
        new_cur = conn_new_db.cursor()

        # Create tables and indexes
        new_cur.execute("""
        -- Drop existing tables if they exist
        DROP TABLE IF EXISTS user_usage_limits;
        DROP TABLE IF EXISTS user_activities;
        DROP TABLE IF EXISTS user_logins;
        DROP TABLE IF EXISTS users;
        DROP TABLE IF EXISTS example_outlines;

        -- Create users table
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255),
            picture_url TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );

        -- Create user_logins table
        CREATE TABLE user_logins (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            login_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );

        -- Create user_activities table
        CREATE TABLE user_activities (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            activity VARCHAR(255),
            lesson_data JSONB,
            activity_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );

        -- Create example_outlines table (without a serial column)
        CREATE TABLE example_outlines (
            name VARCHAR(255) PRIMARY KEY,
            content JSONB NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );

        -- Create user_usage_limits table
        CREATE TABLE user_usage_limits (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            ip_address VARCHAR(45) NOT NULL,
            generations_used INTEGER DEFAULT 0,
            downloads_used INTEGER DEFAULT 0,
            last_reset TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );

        -- Create partial unique indexes:
        -- For anonymous users (user_id IS NULL), ensure ip_address is unique.
        CREATE UNIQUE INDEX idx_user_usage_limits_anonymous 
          ON user_usage_limits(ip_address)
          WHERE user_id IS NULL;

        -- For registered users (user_id IS NOT NULL), ensure each user_id appears only once.
        CREATE UNIQUE INDEX idx_user_usage_limits_registered 
          ON user_usage_limits(user_id)
          WHERE user_id IS NOT NULL;

        -- Additional indexes for performance
        CREATE INDEX idx_user_usage_limits_ip_address ON user_usage_limits(ip_address);
        CREATE INDEX idx_user_usage_limits_last_reset ON user_usage_limits(last_reset);
        """)
        conn_new_db.commit()

        # Create the application user if not exists and grant privileges
        cur.execute(f"SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = '{DB_USER}'")
        if not cur.fetchone():
            cur.execute(f"CREATE USER {DB_USER} WITH PASSWORD '{DB_PASSWORD}'")
            cur.execute(f"GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} TO {DB_USER}")
            print(f"User {DB_USER} created successfully")

        # Connect again to grant table and sequence permissions to the new user
        conn_permissions = psycopg2.connect(
            dbname=DB_NAME,
            user=conn_params['user'],
            password=conn_params['password'],
            host=conn_params['host']
        )
        perm_cur = conn_permissions.cursor()

        # Grant privileges on tables; for tables with serial keys, also grant sequence privileges.
        tables = ['users', 'user_logins', 'user_activities', 'example_outlines', 'user_usage_limits']
        for table in tables:
            perm_cur.execute(f"GRANT ALL PRIVILEGES ON TABLE {table} TO {DB_USER};")
            # example_outlines does not have a serial column
            if table != 'example_outlines':
                perm_cur.execute(f"GRANT ALL PRIVILEGES ON SEQUENCE {table}_id_seq TO {DB_USER};")
        conn_permissions.commit()
        perm_cur.close()
        conn_permissions.close()

        new_cur.close()
        conn_new_db.close()
        cur.close()
        conn.close()
        print("Database and user setup complete!")

    except Exception as e:
        print(f"Error setting up database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_database_and_user()
