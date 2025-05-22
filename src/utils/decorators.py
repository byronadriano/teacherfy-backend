# src/utils/decorators.py
from functools import wraps
from flask import request, jsonify, session
from src.db.usage import check_user_limits, increment_usage
from src.config import logger

def check_usage_limits(action_type='generation', skip_increment=False):
    """
    Decorator to check usage limits before allowing access
    
    Args:
        action_type: 'generation' or 'download' - determines which limit to check
        skip_increment: If True, only checks limits without incrementing usage
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
            
            try:
                # Check limits
                usage = check_user_limits(user_id, ip_address)
                
                # For generation endpoints, check generation limits
                if action_type == 'generation' and not usage['can_generate']:
                    # Calculate next month's reset time
                    from datetime import datetime, timedelta
                    import calendar
                    
                    now = datetime.now()
                    # Get the first day of next month
                    if now.month == 12:
                        next_month = datetime(now.year + 1, 1, 1)
                    else:
                        next_month = datetime(now.year, now.month + 1, 1)
                    
                    reset_time_iso = next_month.isoformat()
                    
                    return jsonify({
                        "error": "Generation limit reached",
                        "limit_reached": True,
                        "require_upgrade": True,
                        "generations_left": 0,
                        "reset_time": reset_time_iso
                    }), 403
                    
                # For download endpoints, we no longer check download limits
                # Downloads are now unlimited once content is generated
                
                # Only increment usage if not skipping and this is a generation action
                if not skip_increment and action_type == 'generation':
                    # Check if this is an example request (shouldn't count against limit)
                    request_data = request.get_json() or {}
                    is_example = (
                        request_data.get("use_example") or
                        (request_data.get("lessonTopic", "").lower().strip() == "equivalent fractions" and
                         request_data.get("gradeLevel", "").lower().strip() == "4th grade" and
                         request_data.get("subjectFocus", "").lower().strip() == "math" and
                         request_data.get("language", "").lower().strip() == "english")
                    )
                    
                    if not is_example:
                        increment_usage(ip_address, user_id, action_type)
                        logger.info(f"Incremented {action_type} usage for {'user ' + str(user_id) if user_id else 'IP ' + ip_address}")
                    else:
                        logger.info(f"Skipping usage increment for example request")
                
                # Call the original function
                result = f(*args, **kwargs)
                
                # CRITICAL FIX: Check if this is a file download response
                # Don't modify file download responses at all
                if isinstance(result, tuple) and len(result) >= 2:
                    response, status_code = result
                    # Check if it's a Flask send_file response (has mimetype)
                    if hasattr(response, 'mimetype'):
                        # Check for file download MIME types
                        file_mime_types = [
                            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                            'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 
                            'application/pdf',
                            'application/octet-stream'
                        ]
                        if any(mime in str(response.mimetype) for mime in file_mime_types):
                            logger.debug(f"File download detected with mimetype {response.mimetype}, returning unmodified response")
                            return result
                
                # Also check for single response objects (Flask send_file returns single response)
                if hasattr(result, 'mimetype'):
                    file_mime_types = [
                        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 
                        'application/pdf',
                        'application/octet-stream'
                    ]
                    if any(mime in str(result.mimetype) for mime in file_mime_types):
                        logger.debug(f"File download detected with mimetype {result.mimetype}, returning unmodified response")
                        return result
                
                # For JSON responses only, add usage limits (only for generation endpoints)
                if action_type == 'generation':
                    if isinstance(result, tuple):
                        response, status_code = result
                        if hasattr(response, 'get_json'):
                            try:
                                response_data = response.get_json() or {}
                                response_data.update({
                                    "usage_limits": {
                                        "generations_left": usage['generations_left'],
                                        "downloads_left": -1,  # Unlimited downloads
                                        "is_premium": user_info.get('is_premium', False)
                                    }
                                })
                                return jsonify(response_data), status_code
                            except:
                                # If we can't parse as JSON, return original
                                return result
                        return result
                    
                    # If the result is a Flask response object with JSON
                    if hasattr(result, 'get_json'):
                        try:
                            response_data = result.get_json() or {}
                            response_data.update({
                                "usage_limits": {
                                    "generations_left": usage['generations_left'],
                                    "downloads_left": -1,  # Unlimited downloads
                                    "is_premium": user_info.get('is_premium', False)
                                }
                            })
                            return jsonify(response_data)
                        except:
                            # If we can't parse as JSON, return original
                            return result
                
                # For all other cases, return the result unchanged
                return result
                
            except Exception as e:
                logger.error(f"Error checking usage limits: {e}", exc_info=True)
                # In case of any error, still allow the request to proceed
                return f(*args, **kwargs)
                
        return decorated_function
    return decorator