# run_migration.py - Run this to add subscription columns
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DB_CONFIG = {
    'dbname': os.environ.get('POSTGRES_DB', 'teacherfy_db'),
    'user': os.environ.get('POSTGRES_USER', 'bpulluta'),
    'password': os.environ.get('POSTGRES_PASSWORD', 'P!p!to031323!'),
    'host': os.environ.get('POSTGRES_HOST', 'teacherfydb.postgres.database.azure.com'),
    'port': os.environ.get('POSTGRES_PORT', '5432'),
    'sslmode': 'require'
}

def run_migration():
    """Add subscription columns to users table"""
    try:
        print("🔧 Connecting to database...")
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        with conn.cursor() as cursor:
            print("🔧 Adding subscription columns to users table...")
            
            # Add subscription columns if they don't exist
            migration_sql = """
            -- Add subscription columns to users table
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS subscription_tier VARCHAR(50) DEFAULT 'free',
            ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(50) DEFAULT 'active',
            ADD COLUMN IF NOT EXISTS subscription_start_date TIMESTAMP WITH TIME ZONE,
            ADD COLUMN IF NOT EXISTS subscription_end_date TIMESTAMP WITH TIME ZONE,
            ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255),
            ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(255);
            
            -- Add hourly tracking columns to user_usage_limits table
            ALTER TABLE user_usage_limits 
            ADD COLUMN IF NOT EXISTS hourly_generations INTEGER DEFAULT 0,
            ADD COLUMN IF NOT EXISTS last_hourly_reset TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
            
            -- Create subscription history table if it doesn't exist
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
            
            -- Add indexes for subscription fields
            CREATE INDEX IF NOT EXISTS idx_user_subscription_tier ON users(subscription_tier);
            CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_id ON user_subscriptions(user_id);
            CREATE INDEX IF NOT EXISTS idx_user_subscriptions_email ON user_subscriptions(email);
            
            -- Update existing users to have default subscription status
            UPDATE users 
            SET subscription_tier = COALESCE(subscription_tier, 'free'),
                subscription_status = COALESCE(subscription_status, 'active')
            WHERE subscription_tier IS NULL OR subscription_tier = '';
            """
            
            # Execute migration SQL
            cursor.execute(migration_sql)
            
            print("✅ Migration completed successfully!")
            print("📊 Checking updated schema...")
            
            # Verify the columns exist
            verification_sql = """
                SELECT column_name, data_type, column_default 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name IN ('subscription_tier', 'subscription_status')
                ORDER BY column_name;
            """
            cursor.execute(verification_sql)
            
            columns = cursor.fetchall()
            print(f"📋 Found {len(columns)} subscription columns:")
            for col in columns:
                print(f"  - {col[0]}: {col[1]} (default: {col[2]})")
                
            # Check user data
            cursor.execute("""
                SELECT id, email, subscription_tier, subscription_status 
                FROM users 
                ORDER BY id 
                LIMIT 5;
            """)
            
            users = cursor.fetchall()
            print(f"👥 Sample user data ({len(users)} users):")
            for user in users:
                print(f"  - ID {user[0]}: {user[1]} | {user[2]} | {user[3]}")
                
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        if conn:
            conn.close()
            print("🔌 Database connection closed")

if __name__ == "__main__":
    run_migration()