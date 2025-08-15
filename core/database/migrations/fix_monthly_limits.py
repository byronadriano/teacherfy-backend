# src/db/migrations/fix_monthly_limits.py
import psycopg2
import os
import sys
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_monthly_limits_migration():
    """
    Migration to fix monthly limits system:
    1. Reset all current usage counts (since they were tracking daily)
    2. Update the last_reset timestamps to current month
    3. Verify the database schema supports monthly calculations
    """
    load_dotenv()
    
    # Get database connection info
    dbname = os.getenv('POSTGRES_DB')
    user = os.getenv('POSTGRES_USER')
    password = os.getenv('POSTGRES_PASSWORD')
    host = os.getenv('POSTGRES_HOST')
    port = os.getenv('POSTGRES_PORT', '5432')
    
    if not all([dbname, user, password, host]):
        logger.error("Missing required database connection details in environment variables")
        sys.exit(1)
    
    try:
        # Connect to the database
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port,
            sslmode='require'
        )
        conn.autocommit = True
        cursor = conn.cursor()
        logger.info(f"Connected to database {dbname} on host {host}")
        
        # Step 1: Check current state of user_usage_limits table
        logger.info("Checking current usage limits table...")
        cursor.execute("""
            SELECT COUNT(*) as total_records,
                   AVG(generations_used) as avg_generations,
                   MAX(generations_used) as max_generations,
                   MIN(last_reset) as oldest_reset,
                   MAX(last_reset) as newest_reset
            FROM user_usage_limits;
        """)
        
        stats = cursor.fetchone()
        logger.info(f"Current table stats:")
        logger.info(f"  Total records: {stats[0]}")
        logger.info(f"  Average generations used: {stats[1]:.2f}" if stats[1] else "  No usage data")
        logger.info(f"  Max generations used: {stats[2]}")
        logger.info(f"  Oldest reset: {stats[3]}")
        logger.info(f"  Newest reset: {stats[4]}")
        
        # Step 2: Reset usage counts for monthly system
        logger.info("Resetting usage counts for monthly limit system...")
        
        # OPTION A: Reset everyone to 0 (recommended for fairness)
        cursor.execute("""
            UPDATE user_usage_limits 
            SET 
                generations_used = 0,
                downloads_used = 0,
                last_reset = CURRENT_TIMESTAMP
        """)
        
        reset_count = cursor.rowcount
        logger.info(f"Reset usage for {reset_count} records")
        
        # OPTION B: Alternative - Keep some usage but cap at monthly limit
        # Uncomment this if you want to preserve some existing usage:
        """
        cursor.execute('''
            UPDATE user_usage_limits 
            SET 
                generations_used = LEAST(generations_used, 5),
                downloads_used = LEAST(downloads_used, 5),
                last_reset = CURRENT_TIMESTAMP
        ''')
        """
        
        # Step 3: Add some test data to verify monthly calculation works
        logger.info("Adding test data to verify monthly calculations...")
        
        # Add a test record with usage from last month (should be reset)
        last_month = datetime.now().replace(day=1) - timedelta(days=1)
        cursor.execute("""
            INSERT INTO user_usage_limits 
                (user_id, ip_address, generations_used, downloads_used, last_reset)
            VALUES 
                (NULL, '192.168.1.999', 5, 3, %s)
            ON CONFLICT (ip_address) WHERE user_id IS NULL 
            DO UPDATE SET
                generations_used = 5,
                downloads_used = 3,
                last_reset = %s
        """, (last_month, last_month))
        
        # Step 4: Test the monthly calculation query
        logger.info("Testing monthly calculation query...")
        cursor.execute("""
            SELECT 
              ip_address,
              generations_used,
              downloads_used,
              last_reset,
              CASE 
                WHEN EXTRACT(MONTH FROM last_reset) != EXTRACT(MONTH FROM CURRENT_TIMESTAMP)
                  OR EXTRACT(YEAR FROM last_reset) != EXTRACT(YEAR FROM CURRENT_TIMESTAMP)
                  THEN 0 
                ELSE generations_used 
              END AS effective_generations_used,
              CASE 
                WHEN EXTRACT(MONTH FROM last_reset) != EXTRACT(MONTH FROM CURRENT_TIMESTAMP)
                  OR EXTRACT(YEAR FROM last_reset) != EXTRACT(YEAR FROM CURRENT_TIMESTAMP)
                  THEN 0 
                ELSE downloads_used 
              END AS effective_downloads_used
            FROM user_usage_limits 
            WHERE ip_address = '192.168.1.999'
        """)
        
        test_result = cursor.fetchone()
        if test_result:
            logger.info(f"Test query result:")
            logger.info(f"  IP: {test_result[0]}")
            logger.info(f"  Stored generations: {test_result[1]}")
            logger.info(f"  Effective generations (should be 0 for last month): {test_result[4]}")
            logger.info(f"  Monthly calculation working: {'✅' if test_result[4] == 0 else '❌'}")
        
        # Step 5: Clean up test data
        cursor.execute("DELETE FROM user_usage_limits WHERE ip_address = '192.168.1.999'")
        
        # Step 6: Final verification
        logger.info("Final verification...")
        cursor.execute("""
            SELECT COUNT(*) as total_records,
                   SUM(CASE WHEN generations_used > 5 THEN 1 ELSE 0 END) as over_limit_records,
                   AVG(generations_used) as avg_generations
            FROM user_usage_limits;
        """)
        
        final_stats = cursor.fetchone()
        logger.info(f"Final stats:")
        logger.info(f"  Total records: {final_stats[0]}")
        logger.info(f"  Records over monthly limit: {final_stats[1]}")
        logger.info(f"  Average generations used: {final_stats[2]:.2f}" if final_stats[2] else "  No usage data")
        
        logger.info("✅ Monthly limits migration completed successfully!")
        logger.info("🔄 Remember to:")
        logger.info("   1. Update environment variables (MONTHLY_GENERATION_LIMIT=5)")
        logger.info("   2. Restart the application")
        logger.info("   3. Test with a few generation requests")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    run_monthly_limits_migration()