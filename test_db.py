#test_db.py
import os
import logging
import traceback
from src.db.database import test_connection
from src.db.usage import check_user_limits, increment_usage

# Configure logging to show more details
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_anonymous_usage():
    """Test anonymous user usage limits"""
    print("\nTesting anonymous user limits...")
    
    # Test IP (ensuring it's a string)
    ip = "127.0.0.1"
    
    try:
        # Check initial limits
        logger.debug(f"Checking initial limits for IP: {ip}")
        limits = check_user_limits(ip_address=ip)
        print(f"Initial limits: {limits}")
        
        # Increment generation count
        print("\nIncrementing generation count...")
        logger.debug("About to call increment_usage")
        increment_usage(ip_address=ip, action_type='generation')
        logger.debug("increment_usage completed")
        
        # Check updated limits
        updated_limits = check_user_limits(ip_address=ip)
        print(f"Updated limits: {updated_limits}")
        
        # Validate limit changes
        if updated_limits['generations_left'] < limits['generations_left']:
            print("✅ Generation limit successfully tracked")
        else:
            print("❌ Generation limit not updated correctly")
    
    except Exception as e:
        print(f"❌ Error testing usage limits: {e}")
        logger.error(traceback.format_exc())
        return False
    
    return True

if __name__ == "__main__":
    # Ensure environment is set up
    required_env_vars = [
        'POSTGRES_DB', 
        'POSTGRES_USER', 
        'POSTGRES_PASSWORD', 
        'POSTGRES_HOST'
    ]
    
    # Check environment variables
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        print("❌ Missing environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        exit(1)
    
    # Run tests
    db_connected = test_connection()
    if db_connected:
        usage_test_passed = test_anonymous_usage()
        
        if usage_test_passed:
            print("\n🎉 All database tests passed successfully!")
        else:
            print("\n❌ Some database tests failed.")
    else:
        print("\n❌ Cannot proceed with further tests.")