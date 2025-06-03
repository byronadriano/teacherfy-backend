# src/db/usage.py - IMPROVED VERSION with clear separation of user vs IP tracking
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
    Only checks user table, never IP-based records.
    """
    # Default to free for anonymous users
    if not user_id and not user_email:
        logger.debug("No user_id or email provided - returning free tier")
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
                    
                    logger.debug(f"User {user_id} has tier: {tier}, status: {status}")
                    
                    if tier == 'premium' and status == 'active':
                        logger.info(f"User {user_id} has active premium subscription")
                        return 'premium'
                    else:
                        logger.info(f"User {user_id} has {tier} subscription with status {status}")
                        return 'free'
            
            # Check by email if we have it and no user_id
            if user_email and not user_id:
                cursor.execute("""
                    SELECT subscription_tier, subscription_status 
                    FROM users 
                    WHERE email = %s
                """, (user_email,))
                
                result = cursor.fetchone()
                if result:
                    tier = result.get('subscription_tier', 'free')
                    status = result.get('subscription_status', 'inactive')
                    
                    logger.debug(f"User {user_email} has tier: {tier}, status: {status}")
                    
                    if tier == 'premium' and status == 'active':
                        logger.info(f"User {user_email} has active premium subscription")
                        return 'premium'
        
        logger.debug(f"User {'ID ' + str(user_id) if user_id else 'email ' + str(user_email)} defaulting to free subscription")
        return 'free'
        
    except Exception as e:
        logger.error(f"Error checking subscription tier: {e}")
        return 'free'

def increment_usage(ip_address=None, user_id=None, action_type='generation'):
    """
    IMPROVED: Increment usage with clear separation between user and IP tracking.
    - If user_id is provided: track by user_id only, ignore ip_address for tracking
    - If no user_id: track by ip_address only (anonymous users)
    """
    logger.info(f"Incrementing {action_type} usage for {'user ' + str(user_id) if user_id else 'IP ' + str(ip_address)}")

    try:
        # Get user's subscription tier (only matters for registered users)
        user_tier = get_user_subscription_tier(user_id, None) if user_id else 'free'
        logger.info(f"User tier: {user_tier}")
        
        # For premium users with unlimited generations, still track for analytics but note unlimited
        if user_tier == 'premium' and action_type == 'generation':
            logger.info("Premium user - tracking for analytics but no limits enforced")
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                if user_id:
                    # REGISTERED USER: Track by user_id only, use placeholder IP
                    logger.debug(f"Tracking usage for registered user {user_id}")
                    cursor.execute("""
                        INSERT INTO user_usage_limits 
                          (user_id, ip_address, generations_used, downloads_used, last_reset)
                        VALUES 
                          (%s, '0.0.0.0', 
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
                          last_reset = CURRENT_TIMESTAMP,
                          ip_address = '0.0.0.0'  -- Always use placeholder for registered users
                    """, (
                        user_id,
                        action_type, action_type,
                        action_type, action_type,
                        action_type, action_type
                    ))
                else:
                    # ANONYMOUS USER: Track by IP only
                    ip_address = sanitize_ip_address(ip_address)
                    if not ip_address:
                        raise ValueError("IP address is required for anonymous users")
                    
                    logger.debug(f"Tracking usage for anonymous IP {ip_address}")
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
            
            conn.commit()
            logger.info(f"Successfully incremented {action_type} usage for {user_tier} {'user' if user_id else 'anonymous'}")
    except Exception as e:
        logger.error(f"Error incrementing usage: {e}")
        logger.error(traceback.format_exc())
        raise

def check_user_limits(user_id=None, ip_address=None):
    """
    IMPROVED: Check usage limits with clear separation.
    - If user_id provided: check user-based limits only
    - If no user_id: check IP-based limits only
    """
    logger.info(f"Checking limits for {'user ' + str(user_id) if user_id else 'IP ' + str(ip_address)}")

    # Get user's subscription tier
    user_tier = get_user_subscription_tier(user_id, None) if user_id else 'free'
    logger.info(f"Checking limits for {user_tier} tier")

    try:
        with get_db_cursor() as cursor:
            if user_id:
                # REGISTERED USER: Check by user_id only
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
                WHERE user_id = %s
                """
                params = (user_id,)
                logger.debug(f"Checking limits for registered user {user_id}")
            else:
                # ANONYMOUS USER: Check by IP only
                ip_address = sanitize_ip_address(ip_address)
                if not ip_address:
                    raise ValueError("IP address is required for anonymous users")
                
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
                WHERE user_id IS NULL AND ip_address = %s
                """
                params = (ip_address,)
                logger.debug(f"Checking limits for anonymous IP {ip_address}")

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
        # Default to allowing requests on error for premium users, restrict for free
        default_tier = get_user_subscription_tier(user_id, None) if user_id else 'free'
        return {
            'can_generate': default_tier == 'premium',
            'can_download': default_tier == 'premium',
            'generations_left': 999999 if default_tier == 'premium' else 0,
            'downloads_left': 999999 if default_tier == 'premium' else 0,
            'reset_time': datetime(2025, 2, 1).isoformat(),
            'current_usage': {
                'generations_used': 0,
                'downloads_used': 0
            },
            'user_tier': default_tier,
            'is_premium': default_tier == 'premium'
        }

def check_and_reset_hourly_limits(user_id, ip_address):
    """IMPROVED: Check hourly limits with proper user vs IP separation."""
    try:
        with get_db_cursor(commit=True) as cursor:
            now = datetime.now()
            
            if user_id:
                # Registered user: check by user_id only
                cursor.execute("""
                    SELECT hourly_generations, last_hourly_reset 
                    FROM user_usage_limits 
                    WHERE user_id = %s
                """, (user_id,))
                logger.debug(f"Checking hourly limits for registered user {user_id}")
            else:
                # Anonymous user: check by IP only
                ip_address = sanitize_ip_address(ip_address)
                cursor.execute("""
                    SELECT hourly_generations, last_hourly_reset 
                    FROM user_usage_limits 
                    WHERE user_id IS NULL AND ip_address = %s
                """, (ip_address,))
                logger.debug(f"Checking hourly limits for anonymous IP {ip_address}")
            
            result = cursor.fetchone()
            
            if not result:
                logger.debug("No hourly usage record found")
                return 0
            
            hourly_generations = result.get('hourly_generations', 0)
            last_hourly_reset = result.get('last_hourly_reset')
            
            if last_hourly_reset:
                if hasattr(last_hourly_reset, 'tzinfo') and last_hourly_reset.tzinfo:
                    last_hourly_reset = last_hourly_reset.replace(tzinfo=None)
                
                if now - last_hourly_reset >= timedelta(hours=1):
                    # Reset hourly limits
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
                    
                    logger.info(f"Reset hourly limits for {'user ' + str(user_id) if user_id else 'IP ' + str(ip_address)}")
                    return 0
            
            return hourly_generations or 0
            
    except Exception as e:
        logger.error(f"Error checking hourly limits: {e}")
        return 0
      
def increment_hourly_usage(user_id, ip_address):
    """IMPROVED: Increment hourly usage with proper user vs IP separation."""
    try:
        with get_db_cursor(commit=True) as cursor:
            now = datetime.now()
            
            if user_id:
                # Registered user: update by user_id only
                cursor.execute("""
                    UPDATE user_usage_limits 
                    SET hourly_generations = COALESCE(hourly_generations, 0) + 1,
                        last_hourly_reset = COALESCE(last_hourly_reset, %s)
                    WHERE user_id = %s
                """, (now, user_id))
                logger.debug(f"Incremented hourly usage for registered user {user_id}")
            else:
                # Anonymous user: update by IP only
                ip_address = sanitize_ip_address(ip_address)
                cursor.execute("""
                    UPDATE user_usage_limits 
                    SET hourly_generations = COALESCE(hourly_generations, 0) + 1,
                        last_hourly_reset = COALESCE(last_hourly_reset, %s)
                    WHERE user_id IS NULL AND ip_address = %s
                """, (now, ip_address))
                logger.debug(f"Incremented hourly usage for anonymous IP {ip_address}")
                
    except Exception as e:
        logger.error(f"Error incrementing hourly usage: {e}")