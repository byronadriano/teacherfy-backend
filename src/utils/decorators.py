# src/utils/decorators.py - IMPROVED with clear user vs IP separation
from functools import wraps
from flask import request, jsonify, session
from src.db.usage_v2 import UsageTracker
from src.config import logger

def is_example_request(request_data):
    """
    COMPREHENSIVE example request detection.
    Returns True if this is an example request that shouldn't count against limits.
    """
    if not request_data:
        return False
    
    # Method 1: Explicit example flag
    if request_data.get("use_example"):
        logger.info("Example request detected: explicit use_example flag")
        return True
    
    # Method 2: Exact match of example form data
    example_indicators = (
        request_data.get("lessonTopic", "").lower().strip() == "equivalent fractions" and
        request_data.get("gradeLevel", "").lower().strip() == "4th grade" and
        request_data.get("subjectFocus", "").lower().strip() == "math" and
        request_data.get("language", "").lower().strip() == "english"
    )
    
    if example_indicators:
        logger.info("Example request detected: matches example form data")
        return True
    
    # Method 3: Check for "isExample" flag in various formats
    if (request_data.get("isExample") or 
        request_data.get("is_example") or 
        request_data.get("example_mode")):
        logger.info("Example request detected: example flag found")
        return True
    
    # Method 4: Check for example in custom prompt
    custom_prompt = request_data.get("custom_prompt", "").lower()
    if "example" in custom_prompt and len(custom_prompt) < 50:  # Short prompt mentioning example
        logger.info("Example request detected: example mentioned in short custom prompt")
        return True
    
    logger.debug("Not an example request")
    return False

def is_test_request(request_data):
    """
    Detect test requests that should count against limits but not make expensive API calls.
    Returns True for test requests.
    """
    if not request_data:
        return False
    
    # Method 1: Explicit test flag
    if request_data.get("test_limits"):
        logger.info("Test request detected: explicit test_limits flag")
        return True
    
    # Method 2: Test topic pattern
    lesson_topic = request_data.get("lessonTopic", "").lower()
    if lesson_topic.startswith("test topic"):
        logger.info("Test request detected: lesson topic starts with 'test topic'")
        return True
    
    # Method 3: Test in custom prompt
    custom_prompt = request_data.get("custom_prompt", "").lower()
    if "test request for limit testing" in custom_prompt:
        logger.info("Test request detected: test phrase in custom prompt")
        return True
    
    # Method 4: Test mode indicators
    if (request_data.get("test_mode") or 
        request_data.get("is_test") or
        request_data.get("testing")):
        logger.info("Test request detected: test mode flag found")
        return True
    
    logger.debug("Not a test request")
    return False

def check_usage_limits(action_type='generation', skip_increment=False):
    """
    IMPROVED: Decorator with clear separation between user and IP tracking.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get user info from session - support both new and legacy session structures
            user_id = session.get('user_id')
            user_email = session.get('user_email')
            
            # Fallback to legacy user_info structure for compatibility
            if not user_id or not user_email:
                user_info = session.get('user_info', {})
                user_id = user_id or user_info.get('id')
                user_email = user_email or user_info.get('email')

            # Critical fix: If we have email but no user_id, resolve it from database
            # This ensures premium users are properly recognized even with incomplete session data
            if not user_id and user_email:
                try:
                    from src.db.database import get_user_by_email as _get_user_by_email
                    user_row = _get_user_by_email(user_email)
                    if user_row and user_row.get('id'):
                        user_id = user_row['id']
                        logger.info(f"Resolved user_id {user_id} from email {user_email}")
                except Exception as lookup_err:
                    logger.warning(f"Could not resolve user_id from email {user_email}: {lookup_err}")
            
            # Get IP address for anonymous users only
            ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
            if ip_address:
                ip_address = ip_address.split(',')[0].strip()
            
            effective_action_type = action_type
            
            # IMPROVED: Clear logging about what we're tracking
            if user_id:
                logger.info(f"Checking {effective_action_type} limits for REGISTERED USER {user_id}")
            else:
                logger.info(f"Checking {effective_action_type} limits for ANONYMOUS IP {ip_address}")
            
            try:
                # Get request data
                request_data = request.get_json() or {}
                
                # CRITICAL: Check if this is an example request BEFORE checking limits
                if is_example_request(request_data):
                    logger.info("EXAMPLE REQUEST DETECTED - Bypassing usage limits and API calls")
                    return f(*args, **kwargs)
                
                # FIXED: Check for regeneration flag - regeneration should count as generation
                is_regeneration = (
                    request_data.get('regeneration') or 
                    request_data.get('regenerationCount', 0) > 0 or
                    request_data.get('previous_outline') or
                    'regenerate' in request.path.lower()
                )
                
                if is_regeneration:
                    logger.info("REGENERATION REQUEST DETECTED - Will count as generation")
                    effective_action_type = 'generation'
                
                # Check if this is a test request (counts against limits but noted for logging)
                is_test = is_test_request(request_data)
                if is_test:
                    logger.info("TEST REQUEST DETECTED - Will count against limits but avoid expensive API calls")
                
                # NEW ROBUST TRACKING: Check limits with clean separation
                limits_result = UsageTracker.check_limits(user_id, ip_address, user_email)
                
                logger.info(f"Limits check: {limits_result}")
                
                # Check hourly limits first
                if limits_result['hourly_exceeded']:
                    logger.warning(f"Hourly limit reached for {limits_result['tracking_method']}")
                    
                    return jsonify({
                        "error": "Rate limit exceeded",
                        "limit_reached": True,
                        "require_upgrade": limits_result['tier'] == 'free',
                        "hourly_limit": limits_result['hourly_limit'],
                        "hourly_used": limits_result['hourly_used'],
                        "user_tier": limits_result['tier'],
                        "reset_time": "1 hour",
                        "tracking_method": limits_result['tracking_method'],
                        "message": f"You've reached your hourly limit of {limits_result['hourly_limit']} generations. {'Upgrade to premium for higher limits!' if limits_result['tier'] == 'free' else 'Please wait an hour before generating more content.'}"
                    }), 429
                
                # Check monthly generation limits (only for free users doing generations)
                if not limits_result['can_generate'] and effective_action_type == 'generation':
                    logger.warning(f"Monthly generation limit reached for {limits_result['tracking_method']}")
                    
                    return jsonify({
                        "error": "Monthly generation limit reached",
                        "limit_reached": True,
                        "require_upgrade": True,
                        "generations_left": limits_result['generations_left'],
                        "generations_used": limits_result['monthly_used']['generations'],
                        "monthly_limit": limits_result['monthly_limits']['generations'],
                        "reset_time": limits_result['reset_time'],
                        "user_tier": limits_result['tier'],
                        "tracking_method": limits_result['tracking_method'],
                        "message": f"You have used all {limits_result['monthly_used']['generations']} of your free monthly generations. Upgrade to premium for unlimited access."
                    }), 403
                
                # Check monthly download limits
                if not limits_result['can_download'] and effective_action_type == 'download':
                    logger.warning(f"Download limit reached for {limits_result['tracking_method']}")
                    
                    return jsonify({
                        "error": "Monthly download limit reached",
                        "limit_reached": True,
                        "require_upgrade": limits_result['tier'] == 'free',
                        "downloads_left": limits_result['downloads_left'],
                        "downloads_used": limits_result['monthly_used']['downloads'],
                        "monthly_limit": limits_result['monthly_limits']['downloads'],
                        "reset_time": limits_result['reset_time'],
                        "user_tier": limits_result['tier'],
                        "tracking_method": limits_result['tracking_method'],
                        "message": f"You have used all {limits_result['monthly_used']['downloads']} of your free monthly downloads. Upgrade to premium for unlimited access."
                    }), 403
                
                # Increment usage BEFORE calling the function (to prevent race conditions)
                if not skip_increment:
                    try:
                        # NEW ROBUST TRACKING: Clean increment with proper separation
                        increment_type = 'generation' if is_regeneration else effective_action_type
                        
                        UsageTracker.increment_usage(increment_type, user_id, ip_address)
                        
                        logger.info(f"Incremented {increment_type} usage for {limits_result['tracking_method']}")
                        
                        if is_test:
                            logger.info("  ^^ This was a TEST REQUEST (no expensive API cost)")
                        if is_regeneration:
                            logger.info("  ^^ This was a REGENERATION REQUEST (counted as generation)")
                    except Exception as increment_error:
                        logger.error(f"Failed to increment usage: {increment_error}")
                        # Continue with the request even if increment fails
                
                # Call the original function
                result = f(*args, **kwargs)
                
                # Check if this is a file download response
                if isinstance(result, tuple) and len(result) >= 2:
                    response, status_code = result
                    if hasattr(response, 'mimetype'):
                        file_mime_types = [
                            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                            'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 
                            'application/pdf',
                            'application/octet-stream'
                        ]
                        if any(mime in str(response.mimetype) for mime in file_mime_types):
                            logger.debug(f"File download detected, returning unmodified response")
                            return result
                
                # Check for single response objects (Flask send_file)
                if hasattr(result, 'mimetype'):
                    file_mime_types = [
                        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 
                        'application/pdf',
                        'application/octet-stream'
                    ]
                    if any(mime in str(result.mimetype) for mime in file_mime_types):
                        logger.debug(f"File download detected, returning unmodified response")
                        return result
                
                # For JSON responses, add updated usage limits (only for generation endpoints)
                if effective_action_type == 'generation' or is_regeneration:
                    # Get updated usage after increment
                    updated_limits = UsageTracker.check_limits(user_id, ip_address, user_email)
                    
                    if isinstance(result, tuple):
                        response, status_code = result
                        if hasattr(response, 'get_json'):
                            try:
                                response_data = response.get_json() or {}
                                response_data.update({
                                    "usage_limits": {
                                        "generations_left": updated_limits['generations_left'],
                                        "downloads_left": updated_limits['downloads_left'],
                                        "reset_time": updated_limits['reset_time'],
                                        "is_premium": updated_limits['tier'] == 'premium',
                                        "user_tier": updated_limits['tier'],
                                        "current_usage": {
                                            "generations_used": updated_limits['monthly_used']['generations'],
                                            "downloads_used": updated_limits['monthly_used']['downloads']
                                        },
                                        "tracking_method": updated_limits['tracking_method']
                                    }
                                })
                                return jsonify(response_data), status_code
                            except:
                                return result
                        return result
                    
                    # If the result is a Flask response object with JSON
                    if hasattr(result, 'get_json'):
                        try:
                            response_data = result.get_json() or {}
                            response_data.update({
                                "usage_limits": {
                                    "generations_left": updated_limits['generations_left'],
                                    "downloads_left": updated_limits['downloads_left'],
                                    "reset_time": updated_limits['reset_time'],
                                    "is_premium": updated_limits['tier'] == 'premium',
                                    "user_tier": updated_limits['tier'],
                                    "current_usage": {
                                        "generations_used": updated_limits['monthly_used']['generations'],
                                        "downloads_used": updated_limits['monthly_used']['downloads']
                                    },
                                    "tracking_method": updated_limits['tracking_method']
                                }
                            })
                            return jsonify(response_data)
                        except:
                            return result
                
                # For all other cases, return the result unchanged
                return result
                
            except Exception as e:
                logger.error(f"Error in usage limits decorator: {e}", exc_info=True)
                # In case of any error, still allow the request to proceed
                return f(*args, **kwargs)
                
        return decorated_function
    return decorator