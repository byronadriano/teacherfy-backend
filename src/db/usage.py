# src/db/usage.py
import os
import logging
import traceback
from datetime import datetime, timedelta
from .database import get_db_cursor, get_db_connection

logger = logging.getLogger(__name__)

# Configuration for usage limits
DAILY_GENERATION_LIMIT = int(os.getenv('DAILY_GENERATION_LIMIT', 3))
DAILY_DOWNLOAD_LIMIT = int(os.getenv('DAILY_DOWNLOAD_LIMIT', 1))

def sanitize_ip_address(ip_address):
    """
    Sanitize the IP address input.
    Handles various input types and converts it to a string.
    """
    if ip_address is None:
        return None

    # If it's a tuple, take the first element
    if isinstance(ip_address, tuple):
        ip_address = ip_address[0]

    ip_address = str(ip_address).strip()

    # Optional basic validation
    try:
        import ipaddress
        ipaddress.ip_address(ip_address)
        return ip_address
    except ValueError:
        logger.warning(f"Invalid IP address format: {ip_address}")
        return ip_address

def increment_usage(ip_address=None, user_id=None, action_type='generation'):
    """
    Increment the usage count for a user or IP address.
    
    Args:
        ip_address (str, optional): The IP address to track.
        user_id (int, optional): The user ID to track.
        action_type (str, optional): Type of action ('generation' or 'download').
    """
    ip_address = sanitize_ip_address(ip_address)
    if not ip_address:
        raise ValueError("IP address is required")

    try:
        if user_id is None:
            # For anonymous users, store user_id as NULL and use the unique index on ip_address.
            query = """
            INSERT INTO user_usage_limits 
              (user_id, ip_address, generations_used, downloads_used, last_reset)
            VALUES 
              (NULL, %s, CASE WHEN %s = 'generation' THEN 1 ELSE 0 END, 
                   CASE WHEN %s = 'download' THEN 1 ELSE 0 END, CURRENT_TIMESTAMP)
            ON CONFLICT (ip_address) WHERE user_id IS NULL DO UPDATE 
            SET 
              generations_used = CASE 
                WHEN user_usage_limits.last_reset < NOW() - INTERVAL '24 hours'
                  THEN CASE WHEN %s = 'generation' THEN 1 ELSE 0 END
                ELSE user_usage_limits.generations_used + CASE WHEN %s = 'generation' THEN 1 ELSE 0 END
              END,
              downloads_used = CASE 
                WHEN user_usage_limits.last_reset < NOW() - INTERVAL '24 hours'
                  THEN CASE WHEN %s = 'download' THEN 1 ELSE 0 END
                ELSE user_usage_limits.downloads_used + CASE WHEN %s = 'download' THEN 1 ELSE 0 END
              END,
              last_reset = CURRENT_TIMESTAMP
            """
            params = (
                ip_address,
                action_type, action_type,
                action_type, action_type,
                action_type, action_type
            )
        else:
            # For registered users, the unique constraint is on user_id.
            query = """
            INSERT INTO user_usage_limits 
              (user_id, ip_address, generations_used, downloads_used, last_reset)
            VALUES 
              (%s, %s, CASE WHEN %s = 'generation' THEN 1 ELSE 0 END, 
                   CASE WHEN %s = 'download' THEN 1 ELSE 0 END, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) DO UPDATE 
            SET 
              generations_used = CASE 
                WHEN user_usage_limits.last_reset < NOW() - INTERVAL '24 hours'
                  THEN CASE WHEN %s = 'generation' THEN 1 ELSE 0 END
                ELSE user_usage_limits.generations_used + CASE WHEN %s = 'generation' THEN 1 ELSE 0 END
              END,
              downloads_used = CASE 
                WHEN user_usage_limits.last_reset < NOW() - INTERVAL '24 hours'
                  THEN CASE WHEN %s = 'download' THEN 1 ELSE 0 END
                ELSE user_usage_limits.downloads_used + CASE WHEN %s = 'download' THEN 1 ELSE 0 END
              END,
              last_reset = CURRENT_TIMESTAMP
            """
            params = (
                user_id, ip_address,
                action_type, action_type,
                action_type, action_type,
                action_type, action_type
            )

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
            conn.commit()
    except Exception as e:
        logger.error(f"Error incrementing usage: {e}")
        logger.error(traceback.format_exc())
        raise

def check_user_limits(user_id=None, ip_address=None):
    """
    Check usage limits for a user or IP address.
    
    Args:
        user_id (int, optional): The user ID to check.
        ip_address (str, optional): The IP address to check.
        
    Returns:
        dict: A dictionary with keys: can_generate, can_download, generations_left, downloads_left.
    """
    ip_address = sanitize_ip_address(ip_address)
    if not ip_address:
        raise ValueError("IP address is required")

    try:
        with get_db_cursor() as cursor:
            query = """
            SELECT 
              COALESCE(
                CASE WHEN last_reset < NOW() - INTERVAL '24 hours'
                  THEN 0 ELSE generations_used END, 0) AS generations_used,
              COALESCE(
                CASE WHEN last_reset < NOW() - INTERVAL '24 hours'
                  THEN 0 ELSE downloads_used END, 0) AS downloads_used
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
                return {
                    'can_generate': True,
                    'can_download': True,
                    'generations_left': DAILY_GENERATION_LIMIT,
                    'downloads_left': DAILY_DOWNLOAD_LIMIT
                }

            generations_left = max(0, DAILY_GENERATION_LIMIT - (usage.get('generations_used') or 0))
            downloads_left = max(0, DAILY_DOWNLOAD_LIMIT - (usage.get('downloads_used') or 0))

            return {
                'can_generate': generations_left > 0,
                'can_download': downloads_left > 0,
                'generations_left': generations_left,
                'downloads_left': downloads_left
            }
    except Exception as e:
        logger.error(f"Error checking user limits: {e}")
        logger.error(traceback.format_exc())
        raise
