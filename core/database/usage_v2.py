# src/db/usage_v2.py - ROBUST TRACKING SYSTEM with clean separation
import os
import logging
import traceback
from datetime import datetime, timedelta
from .database import get_db_cursor, get_db_connection        
from config.settings import logger

logger = logging.getLogger(__name__)

# CLEAR TIER DEFINITIONS
TIER_LIMITS = {
    'free': {
        'monthly_generations': 10,
        'monthly_downloads': 10,
        'hourly_generations': 5
    },
    'premium': {
        'monthly_generations': -1,  # Unlimited
        'monthly_downloads': -1,    # Unlimited
        'hourly_generations': 15
    }
}

class UsageTracker:
    """
    Robust usage tracking with clean separation:
    - Authenticated users: tracked by user_id only
    - Anonymous users: tracked by IP address only
    """
    
    @staticmethod
    def get_user_tier(user_id=None, user_email=None):
        """Get user's subscription tier - only for authenticated users."""
        if not user_id and not user_email:
            return 'free'  # Anonymous users are always free
        
        try:
            with get_db_cursor() as cursor:
                if user_id:
                    cursor.execute("""
                        SELECT subscription_tier, subscription_status 
                        FROM users 
                        WHERE id = %s
                    """, (user_id,))
                else:
                    cursor.execute("""
                        SELECT subscription_tier, subscription_status 
                        FROM users 
                        WHERE email = %s
                    """, (user_email,))
                
                result = cursor.fetchone()
                if result and result.get('subscription_tier') == 'premium' and result.get('subscription_status') == 'active':
                    return 'premium'
                
                return 'free'
        except Exception as e:
            logger.error(f"Error getting user tier: {e}")
            return 'free'
    
    @staticmethod
    def sanitize_ip(ip_address):
        """Clean and validate IP address."""
        if not ip_address:
            return None
        
        if isinstance(ip_address, tuple):
            ip_address = ip_address[0]
        
        ip_address = str(ip_address).strip()
        
        # Handle X-Forwarded-For header
        if ',' in ip_address:
            ip_address = ip_address.split(',')[0].strip()
        
        # Remove port if present
        if ':' in ip_address and not '::' in ip_address:  # IPv4 with port
            ip_address = ip_address.split(':')[0]
        
        return ip_address
    
    @staticmethod
    def get_authenticated_user_usage(user_id):
        """Get usage for authenticated user by user_id only."""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        CASE 
                            WHEN EXTRACT(MONTH FROM last_reset) != EXTRACT(MONTH FROM CURRENT_TIMESTAMP)
                              OR EXTRACT(YEAR FROM last_reset) != EXTRACT(YEAR FROM CURRENT_TIMESTAMP)
                              OR last_reset IS NULL
                              THEN 0 
                            ELSE COALESCE(generations_used, 0) 
                        END AS monthly_generations,
                        CASE 
                            WHEN EXTRACT(MONTH FROM last_reset) != EXTRACT(MONTH FROM CURRENT_TIMESTAMP)
                              OR EXTRACT(YEAR FROM last_reset) != EXTRACT(YEAR FROM CURRENT_TIMESTAMP)
                              OR last_reset IS NULL
                              THEN 0 
                            ELSE COALESCE(downloads_used, 0) 
                        END AS monthly_downloads,
                        CASE 
                            WHEN last_hourly_reset IS NULL 
                              OR CURRENT_TIMESTAMP - last_hourly_reset >= INTERVAL '1 hour'
                              THEN 0 
                            ELSE COALESCE(hourly_generations, 0) 
                        END AS hourly_generations,
                        last_reset,
                        last_hourly_reset
                    FROM user_usage_limits
                    WHERE user_id = %s AND user_id IS NOT NULL
                """, (user_id,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'monthly_generations': result['monthly_generations'],
                        'monthly_downloads': result['monthly_downloads'],
                        'hourly_generations': result['hourly_generations'],
                        'last_reset': result['last_reset'],
                        'last_hourly_reset': result['last_hourly_reset']
                    }
                
                # No record found - return defaults
                return {
                    'monthly_generations': 0,
                    'monthly_downloads': 0,
                    'hourly_generations': 0,
                    'last_reset': None,
                    'last_hourly_reset': None
                }
        except Exception as e:
            logger.error(f"Error getting authenticated user usage: {e}")
            return {
                'monthly_generations': 0,
                'monthly_downloads': 0,
                'hourly_generations': 0,
                'last_reset': None,
                'last_hourly_reset': None
            }
    
    @staticmethod
    def get_anonymous_user_usage(ip_address):
        """Get usage for anonymous user by IP address only."""
        ip_address = UsageTracker.sanitize_ip(ip_address)
        if not ip_address:
            raise ValueError("Valid IP address required for anonymous users")
        
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        CASE 
                            WHEN EXTRACT(MONTH FROM last_reset) != EXTRACT(MONTH FROM CURRENT_TIMESTAMP)
                              OR EXTRACT(YEAR FROM last_reset) != EXTRACT(YEAR FROM CURRENT_TIMESTAMP)
                              OR last_reset IS NULL
                              THEN 0 
                            ELSE COALESCE(generations_used, 0) 
                        END AS monthly_generations,
                        CASE 
                            WHEN EXTRACT(MONTH FROM last_reset) != EXTRACT(MONTH FROM CURRENT_TIMESTAMP)
                              OR EXTRACT(YEAR FROM last_reset) != EXTRACT(YEAR FROM CURRENT_TIMESTAMP)
                              OR last_reset IS NULL
                              THEN 0 
                            ELSE COALESCE(downloads_used, 0) 
                        END AS monthly_downloads,
                        CASE 
                            WHEN last_hourly_reset IS NULL 
                              OR CURRENT_TIMESTAMP - last_hourly_reset >= INTERVAL '1 hour'
                              THEN 0 
                            ELSE COALESCE(hourly_generations, 0) 
                        END AS hourly_generations,
                        last_reset,
                        last_hourly_reset
                    FROM user_usage_limits
                    WHERE ip_address = %s AND user_id IS NULL
                """, (ip_address,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'monthly_generations': result['monthly_generations'],
                        'monthly_downloads': result['monthly_downloads'],
                        'hourly_generations': result['hourly_generations'],
                        'last_reset': result['last_reset'],
                        'last_hourly_reset': result['last_hourly_reset']
                    }
                
                # No record found - return defaults
                return {
                    'monthly_generations': 0,
                    'monthly_downloads': 0,
                    'hourly_generations': 0,
                    'last_reset': None,
                    'last_hourly_reset': None
                }
        except Exception as e:
            logger.error(f"Error getting anonymous user usage: {e}")
            return {
                'monthly_generations': 0,
                'monthly_downloads': 0,
                'hourly_generations': 0,
                'last_reset': None,
                'last_hourly_reset': None
            }
    
    @staticmethod
    def check_limits(user_id=None, ip_address=None, user_email=None):
        """
        Check usage limits with clean separation:
        - If user_id provided: check authenticated user limits
        - If no user_id but ip_address: check anonymous user limits
        """
        if user_id:
            # AUTHENTICATED USER PATH
            tier = UsageTracker.get_user_tier(user_id, user_email)
            usage = UsageTracker.get_authenticated_user_usage(user_id)
            logger.info(f"Checking limits for authenticated user {user_id} (tier: {tier})")
        else:
            # ANONYMOUS USER PATH
            tier = 'free'  # Anonymous users are always free
            usage = UsageTracker.get_anonymous_user_usage(ip_address)
            logger.info(f"Checking limits for anonymous IP {ip_address} (tier: {tier})")
        
        limits = TIER_LIMITS[tier]
        
        # Check limits
        can_generate = True
        can_download = True
        
        # Monthly limits (only apply to free tier)
        if tier == 'free':
            if limits['monthly_generations'] > 0:
                can_generate = usage['monthly_generations'] < limits['monthly_generations']
            if limits['monthly_downloads'] > 0:
                can_download = usage['monthly_downloads'] < limits['monthly_downloads']
        
        # Hourly limits (apply to all tiers)
        hourly_exceeded = usage['hourly_generations'] >= limits['hourly_generations']
        if hourly_exceeded:
            can_generate = False
        
        # Calculate remaining
        if limits['monthly_generations'] == -1:
            generations_left = 999999  # Unlimited
        else:
            generations_left = max(0, limits['monthly_generations'] - usage['monthly_generations'])
        
        if limits['monthly_downloads'] == -1:
            downloads_left = 999999  # Unlimited
        else:
            downloads_left = max(0, limits['monthly_downloads'] - usage['monthly_downloads'])
        
        return {
            'can_generate': can_generate,
            'can_download': can_download,
            'generations_left': generations_left,
            'downloads_left': downloads_left,
            'hourly_exceeded': hourly_exceeded,
            'hourly_used': usage['hourly_generations'],
            'hourly_limit': limits['hourly_generations'],
            'monthly_used': {
                'generations': usage['monthly_generations'],
                'downloads': usage['monthly_downloads']
            },
            'monthly_limits': {
                'generations': limits['monthly_generations'],
                'downloads': limits['monthly_downloads']
            },
            'tier': tier,
            'tracking_method': 'user_id' if user_id else 'ip_address',
            'reset_time': datetime(2025, 2, 1).isoformat()
        }
    
    @staticmethod
    def increment_usage(action_type='generation', user_id=None, ip_address=None):
        """
        Increment usage with clean separation:
        - If user_id provided: increment for authenticated user
        - If no user_id: increment for anonymous user by IP
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    now = datetime.now()
                    
                    if user_id:
                        # AUTHENTICATED USER: Track by user_id only
                        logger.info(f"Incrementing {action_type} for authenticated user {user_id}")
                        
                        cursor.execute("""
                            INSERT INTO user_usage_limits 
                              (user_id, ip_address, generations_used, downloads_used, hourly_generations, last_reset, last_hourly_reset)
                            VALUES 
                              (%s, '0.0.0.0', 
                               CASE WHEN %s = 'generation' THEN 1 ELSE 0 END, 
                               CASE WHEN %s = 'download' THEN 1 ELSE 0 END,
                               CASE WHEN %s = 'generation' THEN 1 ELSE 0 END,
                               %s, %s)
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
                              hourly_generations = CASE 
                                WHEN user_usage_limits.last_hourly_reset IS NULL 
                                  OR CURRENT_TIMESTAMP - user_usage_limits.last_hourly_reset >= INTERVAL '1 hour'
                                  THEN CASE WHEN %s = 'generation' THEN 1 ELSE 0 END
                                ELSE user_usage_limits.hourly_generations + CASE WHEN %s = 'generation' THEN 1 ELSE 0 END
                              END,
                              last_reset = %s,
                              last_hourly_reset = CASE 
                                WHEN user_usage_limits.last_hourly_reset IS NULL 
                                  OR CURRENT_TIMESTAMP - user_usage_limits.last_hourly_reset >= INTERVAL '1 hour'
                                  THEN %s
                                ELSE user_usage_limits.last_hourly_reset
                              END,
                              ip_address = '0.0.0.0'
                        """, (
                            user_id, action_type, action_type, action_type, now, now,
                            action_type, action_type, action_type, action_type, 
                            action_type, action_type, now, now
                        ))
                    
                    else:
                        # ANONYMOUS USER: Track by IP only
                        ip_address = UsageTracker.sanitize_ip(ip_address)
                        if not ip_address:
                            raise ValueError("Valid IP address required for anonymous users")
                        
                        logger.info(f"Incrementing {action_type} for anonymous IP {ip_address}")
                        
                        cursor.execute("""
                            INSERT INTO user_usage_limits 
                              (user_id, ip_address, generations_used, downloads_used, hourly_generations, last_reset, last_hourly_reset)
                            VALUES 
                              (NULL, %s, 
                               CASE WHEN %s = 'generation' THEN 1 ELSE 0 END, 
                               CASE WHEN %s = 'download' THEN 1 ELSE 0 END,
                               CASE WHEN %s = 'generation' THEN 1 ELSE 0 END,
                               %s, %s)
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
                              hourly_generations = CASE 
                                WHEN user_usage_limits.last_hourly_reset IS NULL 
                                  OR CURRENT_TIMESTAMP - user_usage_limits.last_hourly_reset >= INTERVAL '1 hour'
                                  THEN CASE WHEN %s = 'generation' THEN 1 ELSE 0 END
                                ELSE user_usage_limits.hourly_generations + CASE WHEN %s = 'generation' THEN 1 ELSE 0 END
                              END,
                              last_reset = %s,
                              last_hourly_reset = CASE 
                                WHEN user_usage_limits.last_hourly_reset IS NULL 
                                  OR CURRENT_TIMESTAMP - user_usage_limits.last_hourly_reset >= INTERVAL '1 hour'
                                  THEN %s
                                ELSE user_usage_limits.last_hourly_reset
                              END
                        """, (
                            ip_address, action_type, action_type, action_type, now, now,
                            action_type, action_type, action_type, action_type, 
                            action_type, action_type, now, now
                        ))
                
                conn.commit()
                logger.info(f"Successfully incremented {action_type} usage")
                
        except Exception as e:
            logger.error(f"Error incrementing usage: {e}")
            logger.error(traceback.format_exc())
            raise

# Backwards compatibility functions
def get_user_subscription_tier(user_id, user_email=None):
    """Backwards compatibility wrapper."""
    return UsageTracker.get_user_tier(user_id, user_email)

def check_user_limits(user_id=None, ip_address=None):
    """Backwards compatibility wrapper."""
    result = UsageTracker.check_limits(user_id, ip_address)
    return {
        'can_generate': result['can_generate'],
        'can_download': result['can_download'],
        'generations_left': result['generations_left'],
        'downloads_left': result['downloads_left'],
        'reset_time': result['reset_time'],
        'current_usage': {
            'generations_used': result['monthly_used']['generations'],
            'downloads_used': result['monthly_used']['downloads']
        },
        'user_tier': result['tier'],
        'is_premium': result['tier'] == 'premium'
    }

def increment_usage(ip_address=None, user_id=None, action_type='generation'):
    """Backwards compatibility wrapper."""
    return UsageTracker.increment_usage(action_type, user_id, ip_address)

def check_and_reset_hourly_limits(user_id, ip_address):
    """Backwards compatibility wrapper."""
    result = UsageTracker.check_limits(user_id, ip_address)
    return result['hourly_used']

def increment_hourly_usage(user_id, ip_address):
    """Backwards compatibility wrapper - handled automatically in increment_usage."""
    pass

# Keep original HOURLY_LIMITS for backwards compatibility
HOURLY_LIMITS = {
    'free': TIER_LIMITS['free']['hourly_generations'],
    'premium': TIER_LIMITS['premium']['hourly_generations']
}