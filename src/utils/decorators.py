# src/utils/decorators.py
from functools import wraps
from flask import request, jsonify, session
from src.db.usage import check_user_limits, increment_usage
from src.config import logger

def check_usage_limits(action_type='generation'):
    """Decorator to check usage limits before allowing access"""
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
                
                if action_type == 'generation' and not usage['can_generate']:
                    return jsonify({
                        "error": "Generation limit reached",
                        "limit_reached": True,
                        "require_upgrade": True
                    }), 403
                    
                if action_type == 'download' and not usage['can_download']:
                    return jsonify({
                        "error": "Download limit reached",
                        "limit_reached": True,
                        "require_upgrade": True
                    }), 403
                
                # If within limits, increment usage and proceed
                increment_usage(ip_address, user_id, action_type)
                
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
                
                # For JSON responses only, add usage limits
                if isinstance(result, tuple):
                    response, status_code = result
                    if hasattr(response, 'get_json'):
                        try:
                            response_data = response.get_json() or {}
                            response_data.update({
                                "usage_limits": {
                                    "generations_left": usage['generations_left'],
                                    "downloads_left": usage['downloads_left']
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
                                "downloads_left": usage['downloads_left']
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