# src/utils/decorators.py - FIXED to ensure regeneration counts as generation
from functools import wraps
from flask import request, jsonify, session
from src.db.usage import check_user_limits, increment_usage, check_and_reset_hourly_limits, increment_hourly_usage, HOURLY_LIMITS, get_user_subscription_tier
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
    FIXED: Decorator that properly counts regeneration as generation and enforces tier limits.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get user info from session
            user_info = session.get('user_info', {})
            user_id = user_info.get('id')
            
            # Get IP address for anonymous users
            ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
            if ip_address:
                ip_address = ip_address.split(',')[0].strip()
            
            # FIXED: Use a different variable name to avoid shadowing the parameter
            effective_action_type = action_type
            
            logger.info(f"Checking {effective_action_type} limits for {'user ' + str(user_id) if user_id else 'IP ' + ip_address}")
            
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
                    effective_action_type = 'generation'  # Force regeneration to count as generation
                
                # Check if this is a test request (counts against limits but noted for logging)
                is_test = is_test_request(request_data)
                if is_test:
                    logger.info("TEST REQUEST DETECTED - Will count against limits but avoid expensive API calls")
                
                # Get user's actual subscription tier
                user_email = user_info.get('email') if user_info else None
                user_tier = get_user_subscription_tier(user_id, user_email)
                
                # Check hourly limits first
                current_hourly_usage = check_and_reset_hourly_limits(user_id, ip_address)
                hourly_limit = HOURLY_LIMITS.get(user_tier, 3)
                
                logger.info(f"User tier: {user_tier}, hourly limit: {hourly_limit}, current usage: {current_hourly_usage}")
                
                if current_hourly_usage >= hourly_limit:
                    logger.warning(f"Hourly limit reached for {'user ' + str(user_id) if user_id else 'IP ' + ip_address}")
                    
                    return jsonify({
                        "error": "Rate limit exceeded",
                        "limit_reached": True,
                        "require_upgrade": user_tier == 'free',
                        "hourly_limit": hourly_limit,
                        "hourly_used": current_hourly_usage,
                        "user_tier": user_tier,
                        "reset_time": "1 hour",
                        "message": f"You've reached your hourly limit of {hourly_limit} generations. {'Upgrade to premium for higher limits!' if user_tier == 'free' else 'Please wait an hour before generating more content.'}"
                    }), 429
                
                # Check monthly limits (only for free users)
                if user_tier == 'free' and effective_action_type == 'generation':
                    usage = check_user_limits(user_id, ip_address)
                    
                    if not usage['can_generate']:
                        logger.warning(f"Monthly generation limit reached for {'user ' + str(user_id) if user_id else 'IP ' + ip_address}")
                        
                        return jsonify({
                            "error": "Monthly generation limit reached",
                            "limit_reached": True,
                            "require_upgrade": True,
                            "generations_left": 0,
                            "generations_used": usage['current_usage']['generations_used'],
                            "monthly_limit": 10,
                            "reset_time": usage.get('reset_time'),
                            "user_tier": user_tier,
                            "message": f"You have used all {usage['current_usage']['generations_used']} of your free monthly generations. Upgrade to premium for unlimited access."
                        }), 403
                
                # For download endpoints, check download limits
                if effective_action_type == 'download':
                    usage = check_user_limits(user_id, ip_address)
                    if not usage['can_download']:
                        logger.warning(f"Download limit reached for {'user ' + str(user_id) if user_id else 'IP ' + ip_address}")
                        
                        return jsonify({
                            "error": "Monthly download limit reached",
                            "limit_reached": True,
                            "require_upgrade": user_tier == 'free',
                            "downloads_left": 0,
                            "downloads_used": usage['current_usage']['downloads_used'],
                            "monthly_limit": 10,
                            "reset_time": usage.get('reset_time'),
                            "user_tier": user_tier,
                            "message": f"You have used all {usage['current_usage']['downloads_used']} of your free monthly downloads. Upgrade to premium for unlimited access."
                        }), 403
                
                # Increment usage BEFORE calling the function (to prevent race conditions)
                if not skip_increment:
                    try:
                        # FIXED: Always increment for regeneration as generation
                        increment_type = 'generation' if is_regeneration else effective_action_type
                        increment_usage(ip_address, user_id, increment_type)
                        logger.info(f"Incremented {increment_type} usage for {'user ' + str(user_id) if user_id else 'IP ' + ip_address}")
                        
                        # Also increment hourly usage
                        increment_hourly_usage(user_id, ip_address)
                        
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
                    updated_usage = check_user_limits(user_id, ip_address)
                    
                    if isinstance(result, tuple):
                        response, status_code = result
                        if hasattr(response, 'get_json'):
                            try:
                                response_data = response.get_json() or {}
                                response_data.update({
                                    "usage_limits": {
                                        "generations_left": updated_usage['generations_left'],
                                        "downloads_left": updated_usage['downloads_left'],
                                        "reset_time": updated_usage['reset_time'],
                                        "is_premium": user_tier == 'premium',
                                        "user_tier": user_tier,
                                        "current_usage": updated_usage['current_usage']
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
                                    "generations_left": updated_usage['generations_left'],
                                    "downloads_left": updated_usage['downloads_left'],
                                    "reset_time": updated_usage['reset_time'],
                                    "is_premium": user_tier == 'premium',
                                    "user_tier": user_tier,
                                    "current_usage": updated_usage['current_usage']
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