# src/db/usage.py - FIXED VERSION with correct tier limits
import os
import logging
import traceback
from datetime import datetime, timedelta
from .database import get_db_cursor, get_db_connection        
from src.config import logger

logger = logging.getLogger(__name__)

# FIXED: Correct limits as requested
def get_generation_limit(tier='free'):
    """Get generation limit based on tier"""
    if tier == 'premium':
        return -1  # Unlimited
    return 10  # Free tier: 10 per month

def get_download_limit(tier='free'):
    """Get download limit based on tier"""
    if tier == 'premium':
        return -1  # Unlimited
    return 10  # Free tier: 10 per month

# FIXED: Correct hourly limits as requested
HOURLY_LIMITS = {
    'free': 3,      # Free users: 3 generations per hour
    'premium': 10   # Premium users: 10 generations per hour
}

def sanitize_ip_address(ip_address):
    """Sanitize the IP address input."""
    if ip_address is None:
        return None

    if isinstance(ip_address, tuple):
        ip_address = ip_address[0]

    ip_address = str(ip_address).strip()
    
    if ':' in ip_address:
        ip_address = ip_address.split(':')[0]

    try:
        import ipaddress
        ipaddress.ip_address(ip_address)
        return ip_address
    except ValueError:
        logger.warning(f"Invalid IP address format: {ip_address}")
        return ip_address

def get_user_subscription_tier(user_id, user_email=None):
    """
    Get user's subscription tier. Returns 'free' or 'premium'.
    """
    from src.db.database import get_db_cursor
    
    # Default to free for anonymous users
    if not user_id and not user_email:
        return 'free'
    
    try:
        with get_db_cursor() as cursor:
            # FIXED: Check the users table for subscription info
            if user_id:
                cursor.execute("""
                    SELECT subscription_tier, subscription_status 
                    FROM users 
                    WHERE id = %s
                """, (user_id,))
                
                result = cursor.fetchone()
                if result:
                    tier = result.get('subscription_tier', 'free')
                    status = result.get('subscription_status', 'inactive')
                    
                    if tier == 'premium' and status == 'active':
                        logger.info(f"User {user_id} has active premium subscription")
                        return 'premium'
            
            # Check by email if we have it
            if user_email:
                cursor.execute("""
                    SELECT subscription_tier, subscription_status 
                    FROM users 
                    WHERE email = %s
                """, (user_email,))
                
                result = cursor.fetchone()
                if result:
                    tier = result.get('subscription_tier', 'free')
                    status = result.get('subscription_status', 'inactive')
                    
                    if tier == 'premium' and status == 'active':
                        logger.info(f"User {user_email} has active premium subscription")
                        return 'premium'
        
        logger.debug(f"User {'ID ' + str(user_id) if user_id else 'email ' + str(user_email)} has free subscription")
        return 'free'
        
    except Exception as e:
        logger.error(f"Error checking subscription tier: {e}")
        return 'free'

def increment_usage(ip_address=None, user_id=None, action_type='generation'):
    """
    Increment the usage count for a user or IP address with tier-aware MONTHLY limits.
    """
    ip_address = sanitize_ip_address(ip_address)
    if not ip_address:
        raise ValueError("IP address is required")

    logger.info(f"Incrementing {action_type} usage for {'user ' + str(user_id) if user_id else 'IP ' + ip_address}")

    try:
        # Get user's subscription tier
        user_tier = get_user_subscription_tier(user_id, None)
        logger.info(f"User tier: {user_tier}")
        
        # For premium users with unlimited generations, don't track monthly limits
        if user_tier == 'premium' and action_type == 'generation':
            logger.info("Premium user - skipping monthly generation limit tracking")
            # Still track for analytics but don't enforce limits
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                if user_id is None:
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
            logger.info(f"Successfully incremented {action_type} usage for {user_tier} user")
    except Exception as e:
        logger.error(f"Error incrementing usage: {e}")
        logger.error(traceback.format_exc())
        raise

def check_user_limits(user_id=None, ip_address=None):
    """
    Check usage limits for a user or IP address with tier awareness.
    """
    ip_address = sanitize_ip_address(ip_address)
    if not ip_address:
        raise ValueError("IP address is required")

    # Get user's subscription tier
    user_tier = get_user_subscription_tier(user_id, None)
    logger.info(f"Checking limits for {user_tier} user {'ID ' + str(user_id) if user_id else 'IP ' + ip_address}")

    try:
        with get_db_cursor() as cursor:
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

            # Get limits based on tier
            gen_limit = get_generation_limit(user_tier)
            dl_limit = get_download_limit(user_tier)

            if not usage:
                # No usage record found
                logger.info("No usage record found - within limits")
                return {
                    'can_generate': True,
                    'can_download': True,
                    'generations_left': gen_limit if gen_limit > 0 else 999999,
                    'downloads_left': dl_limit if dl_limit > 0 else 999999,
                    'reset_time': datetime(2025, 2, 1).isoformat(),
                    'current_usage': {
                        'generations_used': 0,
                        'downloads_used': 0
                    },
                    'user_tier': user_tier,
                    'is_premium': user_tier == 'premium'
                }

            current_generations = usage.get('current_generations_used', 0)
            current_downloads = usage.get('current_downloads_used', 0)
            
            # Calculate remaining limits
            if gen_limit == -1:  # Unlimited for premium
                generations_left = 999999
                can_generate = True
            else:
                generations_left = max(0, gen_limit - current_generations)
                can_generate = generations_left > 0
            
            if dl_limit == -1:  # Unlimited for premium
                downloads_left = 999999
                can_download = True
            else:
                downloads_left = max(0, dl_limit - current_downloads)
                can_download = downloads_left > 0

            logger.info(f"Current usage: {current_generations}/{gen_limit if gen_limit > 0 else 'unlimited'} generations, {current_downloads}/{dl_limit if dl_limit > 0 else 'unlimited'} downloads")

            return {
                'can_generate': can_generate,
                'can_download': can_download,
                'generations_left': generations_left,
                'downloads_left': downloads_left,
                'reset_time': datetime(2025, 2, 1).isoformat(),
                'current_usage': {
                    'generations_used': current_generations,
                    'downloads_used': current_downloads
                },
                'user_tier': user_tier,
                'is_premium': user_tier == 'premium'
            }
    except Exception as e:
        logger.error(f"Error checking user limits: {e}")
        logger.error(traceback.format_exc())
        # Default to allowing requests on error
        return {
            'can_generate': True,
            'can_download': True,
            'generations_left': 10,
            'downloads_left': 10,
            'reset_time': datetime(2025, 2, 1).isoformat(),
            'current_usage': {
                'generations_used': 0,
                'downloads_used': 0
            },
            'user_tier': 'free',
            'is_premium': False
        }

def check_and_reset_hourly_limits(user_id, ip_address):
    """Check and reset hourly limits, return current hourly usage."""
    try:
        with get_db_cursor(commit=True) as cursor:
            now = datetime.now()
            
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
                return 0
            
            hourly_generations = result.get('hourly_generations', 0)
            last_hourly_reset = result.get('last_hourly_reset')
            
            if last_hourly_reset:
                if hasattr(last_hourly_reset, 'tzinfo') and last_hourly_reset.tzinfo:
                    last_hourly_reset = last_hourly_reset.replace(tzinfo=None)
                
                if now - last_hourly_reset >= timedelta(hours=1):
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
    """Increment hourly usage counter."""
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