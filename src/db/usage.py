# src/db/usage.py - FIXED VERSION with proper monthly limits
import os
import logging
import traceback
from datetime import datetime, timedelta
from .database import get_db_cursor, get_db_connection        
from src.config import logger

logger = logging.getLogger(__name__)

# DEVELOPMENT: Use higher limits for testing
def get_generation_limit():
    """Get generation limit based on environment"""
    if os.getenv('FLASK_ENV') == 'development':
        return int(os.getenv('MONTHLY_GENERATION_LIMIT', 15))  # Higher limit for dev
    return int(os.getenv('MONTHLY_GENERATION_LIMIT', 5))  # Production limit

def get_download_limit():
    """Get download limit based on environment"""
    if os.getenv('FLASK_ENV') == 'development':
        return int(os.getenv('MONTHLY_DOWNLOAD_LIMIT', 15))  # Higher limit for dev
    return int(os.getenv('MONTHLY_DOWNLOAD_LIMIT', 5))  # Production limit

MONTHLY_GENERATION_LIMIT = get_generation_limit()
MONTHLY_DOWNLOAD_LIMIT = get_download_limit()

def sanitize_ip_address(ip_address):
    """Sanitize the IP address input."""
    if ip_address is None:
        return None

    if isinstance(ip_address, tuple):
        ip_address = ip_address[0]

    ip_address = str(ip_address).strip()
    
    # Handle IP addresses that come with port numbers (e.g., "192.168.1.1:8080")
    if ':' in ip_address:
        ip_address = ip_address.split(':')[0]

    try:
        import ipaddress
        ipaddress.ip_address(ip_address)
        return ip_address
    except ValueError:
        logger.warning(f"Invalid IP address format: {ip_address}")
        return ip_address

def is_new_month(last_reset_time):
    """Check if we're in a new month compared to the last reset time."""
    if not last_reset_time:
        return True
        
    now = datetime.now()
    
    # FIXED: More robust month comparison
    if hasattr(last_reset_time, 'tzinfo') and last_reset_time.tzinfo:
        last_reset_time = last_reset_time.replace(tzinfo=None)
    
    # If different year OR different month, it's a new month
    return (now.year != last_reset_time.year or 
            now.month != last_reset_time.month)

def get_monthly_reset_time():
    """Get the timestamp for when limits will reset (first day of next month)."""
    now = datetime.now()
    
    # Calculate first day of next month
    if now.month == 12:
        next_month = datetime(now.year + 1, 1, 1)
    else:
        next_month = datetime(now.year, now.month + 1, 1)
    
    return next_month

def increment_usage(ip_address=None, user_id=None, action_type='generation'):
    """
    Increment the usage count for a user or IP address with MONTHLY limits.
    
    Args:
        ip_address (str, optional): The IP address to track.
        user_id (int, optional): The user ID to track.
        action_type (str, optional): Type of action ('generation' or 'download').
    """
    ip_address = sanitize_ip_address(ip_address)
    if not ip_address:
        raise ValueError("IP address is required")

    logger.info(f"Incrementing {action_type} usage for {'user ' + str(user_id) if user_id else 'IP ' + ip_address}")

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                if user_id is None:
                    # FIXED: Better upsert logic for anonymous users
                    cursor.execute("""
                        INSERT INTO user_usage_limits 
                          (user_id, ip_address, generations_used, downloads_used, last_reset)
                        VALUES 
                          (NULL, %s, 
                           CASE WHEN %s = 'generation' THEN 1 ELSE 0 END, 
                           CASE WHEN %s = 'download' THEN 1 ELSE 0 END, 
                           CURRENT_TIMESTAMP)
                        ON CONFLICT (ip_address) WHERE user_id IS NULL DO UPDATE 
                        SET 
                          generations_used = CASE 
                            WHEN EXTRACT(MONTH FROM user_usage_limits.last_reset) != EXTRACT(MONTH FROM CURRENT_TIMESTAMP)
                              OR EXTRACT(YEAR FROM user_usage_limits.last_reset) != EXTRACT(YEAR FROM CURRENT_TIMESTAMP)
                              THEN CASE WHEN %s = 'generation' THEN 1 ELSE 0 END
                            ELSE user_usage_limits.generations_used + CASE WHEN %s = 'generation' THEN 1 ELSE 0 END
                          END,
                          downloads_used = CASE 
                            WHEN EXTRACT(MONTH FROM user_usage_limits.last_reset) != EXTRACT(MONTH FROM CURRENT_TIMESTAMP)
                              OR EXTRACT(YEAR FROM user_usage_limits.last_reset) != EXTRACT(YEAR FROM CURRENT_TIMESTAMP)
                              THEN CASE WHEN %s = 'download' THEN 1 ELSE 0 END
                            ELSE user_usage_limits.downloads_used + CASE WHEN %s = 'download' THEN 1 ELSE 0 END
                          END,
                          last_reset = CURRENT_TIMESTAMP
                    """, (
                        ip_address,
                        action_type, action_type,
                        action_type, action_type,
                        action_type, action_type
                    ))
                else:
                    # FIXED: Better upsert logic for registered users
                    cursor.execute("""
                        INSERT INTO user_usage_limits 
                          (user_id, ip_address, generations_used, downloads_used, last_reset)
                        VALUES 
                          (%s, %s, 
                           CASE WHEN %s = 'generation' THEN 1 ELSE 0 END, 
                           CASE WHEN %s = 'download' THEN 1 ELSE 0 END, 
                           CURRENT_TIMESTAMP)
                        ON CONFLICT (user_id) WHERE user_id IS NOT NULL DO UPDATE 
                        SET 
                          generations_used = CASE 
                            WHEN EXTRACT(MONTH FROM user_usage_limits.last_reset) != EXTRACT(MONTH FROM CURRENT_TIMESTAMP)
                              OR EXTRACT(YEAR FROM user_usage_limits.last_reset) != EXTRACT(YEAR FROM CURRENT_TIMESTAMP)
                              THEN CASE WHEN %s = 'generation' THEN 1 ELSE 0 END
                            ELSE user_usage_limits.generations_used + CASE WHEN %s = 'generation' THEN 1 ELSE 0 END
                          END,
                          downloads_used = CASE 
                            WHEN EXTRACT(MONTH FROM user_usage_limits.last_reset) != EXTRACT(MONTH FROM CURRENT_TIMESTAMP)
                              OR EXTRACT(YEAR FROM user_usage_limits.last_reset) != EXTRACT(YEAR FROM CURRENT_TIMESTAMP)
                              THEN CASE WHEN %s = 'download' THEN 1 ELSE 0 END
                            ELSE user_usage_limits.downloads_used + CASE WHEN %s = 'download' THEN 1 ELSE 0 END
                          END,
                          last_reset = CURRENT_TIMESTAMP
                    """, (
                        user_id, ip_address,
                        action_type, action_type,
                        action_type, action_type,
                        action_type, action_type
                    ))
            
            conn.commit()
            logger.info(f"Successfully incremented {action_type} usage")
    except Exception as e:
        logger.error(f"Error incrementing usage: {e}")
        logger.error(traceback.format_exc())
        raise

def check_user_limits(user_id=None, ip_address=None):
    """
    Check MONTHLY usage limits for a user or IP address.
    
    Args:
        user_id (int, optional): The user ID to check.
        ip_address (str, optional): The IP address to check.
        
    Returns:
        dict: A dictionary with usage information and limits.
    """
    ip_address = sanitize_ip_address(ip_address)
    if not ip_address:
        raise ValueError("IP address is required")

    logger.info(f"Checking monthly limits for {'user ' + str(user_id) if user_id else 'IP ' + ip_address}")

    try:
        with get_db_cursor() as cursor:
            # FIXED: Proper month comparison using EXTRACT
            query = """
            SELECT 
              CASE 
                WHEN EXTRACT(MONTH FROM last_reset) != EXTRACT(MONTH FROM CURRENT_TIMESTAMP)
                  OR EXTRACT(YEAR FROM last_reset) != EXTRACT(YEAR FROM CURRENT_TIMESTAMP)
                  OR last_reset IS NULL
                  THEN 0 
                ELSE COALESCE(generations_used, 0) 
              END AS current_generations_used,
              CASE 
                WHEN EXTRACT(MONTH FROM last_reset) != EXTRACT(MONTH FROM CURRENT_TIMESTAMP)
                  OR EXTRACT(YEAR FROM last_reset) != EXTRACT(YEAR FROM CURRENT_TIMESTAMP)
                  OR last_reset IS NULL
                  THEN 0 
                ELSE COALESCE(downloads_used, 0) 
              END AS current_downloads_used,
              last_reset
            FROM user_usage_limits
            WHERE 
            """
            
            if user_id is not None:
                query += "user_id = %s"
                params = (user_id,)
            else:
                query += "user_id IS NULL AND ip_address = %s"
                params = (ip_address,)

            cursor.execute(query, params)
            usage = cursor.fetchone()

            if not usage:
                # No usage record found - user/IP is within limits
                logger.info("No usage record found - within limits")
                gen_limit = get_generation_limit()
                dl_limit = get_download_limit()
                return {
                    'can_generate': True,
                    'can_download': True,
                    'generations_left': gen_limit,
                    'downloads_left': dl_limit,
                    'reset_time': get_monthly_reset_time().isoformat(),
                    'current_usage': {
                        'generations_used': 0,
                        'downloads_used': 0
                    }
                }

            current_generations = usage.get('current_generations_used', 0)
            current_downloads = usage.get('current_downloads_used', 0)
            
            generations_left = max(0, MONTHLY_GENERATION_LIMIT - current_generations)
            downloads_left = max(0, MONTHLY_DOWNLOAD_LIMIT - current_downloads)

            logger.info(f"Current usage: {current_generations}/{MONTHLY_GENERATION_LIMIT} generations, {current_downloads}/{MONTHLY_DOWNLOAD_LIMIT} downloads")
            logger.info(f"Remaining: {generations_left} generations, {downloads_left} downloads")

            return {
                'can_generate': generations_left > 0,
                'can_download': downloads_left > 0,
                'generations_left': generations_left,
                'downloads_left': downloads_left,
                'reset_time': get_monthly_reset_time().isoformat(),
                'current_usage': {
                    'generations_used': current_generations,
                    'downloads_used': current_downloads
                }
            }
    except Exception as e:
        logger.error(f"Error checking user limits: {e}")
        logger.error(traceback.format_exc())
        # In case of error, allow the request to prevent blocking users
        return {
            'can_generate': True,
            'can_download': True,
            'generations_left': MONTHLY_GENERATION_LIMIT,
            'downloads_left': MONTHLY_DOWNLOAD_LIMIT,
            'reset_time': get_monthly_reset_time().isoformat(),
            'current_usage': {
                'generations_used': 0,
                'downloads_used': 0
            }
        }

def check_and_reset_hourly_limits(user_id, ip_address):
    """
    Check if hourly limits need to be reset and return current hourly usage.
    FIXED: Handle timezone-aware and timezone-naive datetime objects properly.
    """
    from src.db.database import get_db_cursor
    
    try:
        with get_db_cursor(commit=True) as cursor:
            now = datetime.now()
            
            # Get current usage record
            if user_id:
                cursor.execute("""
                    SELECT hourly_generations, last_hourly_reset 
                    FROM user_usage_limits 
                    WHERE user_id = %s
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT hourly_generations, last_hourly_reset 
                    FROM user_usage_limits 
                    WHERE user_id IS NULL AND ip_address = %s
                """, (ip_address,))
            
            result = cursor.fetchone()
            
            if not result:
                # No record exists yet, will be created by existing increment_usage function
                return 0
            
            hourly_generations = result.get('hourly_generations', 0)
            last_hourly_reset = result.get('last_hourly_reset')
            
            # FIXED: Handle timezone-aware datetime properly
            if last_hourly_reset:
                # Convert timezone-aware datetime to naive if needed
                if hasattr(last_hourly_reset, 'tzinfo') and last_hourly_reset.tzinfo:
                    last_hourly_reset = last_hourly_reset.replace(tzinfo=None)
                
                # Check if we need to reset hourly counter (if more than 1 hour has passed)
                if now - last_hourly_reset >= timedelta(hours=1):
                    # Reset hourly counter
                    if user_id:
                        cursor.execute("""
                            UPDATE user_usage_limits 
                            SET hourly_generations = 0, last_hourly_reset = %s
                            WHERE user_id = %s
                        """, (now, user_id))
                    else:
                        cursor.execute("""
                            UPDATE user_usage_limits 
                            SET hourly_generations = 0, last_hourly_reset = %s
                            WHERE user_id IS NULL AND ip_address = %s
                        """, (now, ip_address))
                    
                    logger.info(f"Reset hourly limits for {'user ' + str(user_id) if user_id else 'IP ' + ip_address}")
                    return 0
            
            return hourly_generations or 0
            
    except Exception as e:
        logger.error(f"Error checking hourly limits: {e}")
        return 0
      
def increment_hourly_usage(user_id, ip_address):
    """
    Increment hourly usage counter. 
    This works alongside the existing increment_usage function.
    """
    from src.db.database import get_db_cursor
    
    try:
        with get_db_cursor(commit=True) as cursor:
            now = datetime.now()
            
            if user_id:
                cursor.execute("""
                    UPDATE user_usage_limits 
                    SET hourly_generations = COALESCE(hourly_generations, 0) + 1,
                        last_hourly_reset = COALESCE(last_hourly_reset, %s)
                    WHERE user_id = %s
                """, (now, user_id))
            else:
                cursor.execute("""
                    UPDATE user_usage_limits 
                    SET hourly_generations = COALESCE(hourly_generations, 0) + 1,
                        last_hourly_reset = COALESCE(last_hourly_reset, %s)
                    WHERE user_id IS NULL AND ip_address = %s
                """, (now, ip_address))
                
    except Exception as e:
        logger.error(f"Error incrementing hourly usage: {e}")

# Simple rate limit configuration (we'll make this more sophisticated later)
HOURLY_LIMITS = {
    'free': 3,      # Free users: 3 generations per hour
    'premium': 15   # Premium users: 15 generations per hour (we'll add subscription detection later)
}

# Add this to your existing src/db/usage.py file

def get_user_subscription_tier(user_id, user_email=None):
    """
    Get user's subscription tier. Returns 'free' or 'premium'.
    This is a simple version - we'll enhance it later with Stripe integration.
    """
    from src.db.database import get_db_cursor
    
    # Default to free for anonymous users
    if not user_id and not user_email:
        return 'free'
    
    try:
        with get_db_cursor() as cursor:
            # Check by user_id first
            if user_id:
                cursor.execute("""
                    SELECT subscription_status 
                    FROM user_subscriptions 
                    WHERE user_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT 1
                """, (user_id,))
                
                result = cursor.fetchone()
                if result and result['subscription_status'] == 'premium':
                    logger.info(f"User {user_id} has premium subscription")
                    return 'premium'
            
            # Check by email if we have it
            if user_email:
                cursor.execute("""
                    SELECT subscription_status 
                    FROM user_subscriptions 
                    WHERE email = %s 
                    ORDER BY created_at DESC 
                    LIMIT 1
                """, (user_email,))
                
                result = cursor.fetchone()
                if result and result['subscription_status'] == 'premium':
                    logger.info(f"User {user_email} has premium subscription")
                    return 'premium'
        
        logger.debug(f"User {'ID ' + str(user_id) if user_id else 'email ' + str(user_email)} has free subscription")
        return 'free'
        
    except Exception as e:
        logger.error(f"Error checking subscription tier: {e}")
        # Default to free on error
        return 'free'

# Update the hourly limits for premium users
HOURLY_LIMITS = {
    'free': 3,      # Free users: 3 generations per hour
    'premium': 20   # Premium users: 20 generations per hour
}