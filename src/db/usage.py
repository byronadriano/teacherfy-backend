# src/db/usage.py - FIXED VERSION with proper monthly limits
import os
import logging
import traceback
from datetime import datetime, timedelta
from .database import get_db_cursor, get_db_connection

logger = logging.getLogger(__name__)

# FIXED: Use monthly limits consistently
MONTHLY_GENERATION_LIMIT = int(os.getenv('MONTHLY_GENERATION_LIMIT', 5))  # Changed from daily to monthly
MONTHLY_DOWNLOAD_LIMIT = int(os.getenv('MONTHLY_DOWNLOAD_LIMIT', 5))      # Changed from daily to monthly

def sanitize_ip_address(ip_address):
    """Sanitize the IP address input."""
    if ip_address is None:
        return None

    if isinstance(ip_address, tuple):
        ip_address = ip_address[0]

    ip_address = str(ip_address).strip()

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