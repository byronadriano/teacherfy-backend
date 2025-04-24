from functools import wraps
from flask import request, jsonify, session, send_file
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
                
                # IMPORTANT FIX: Don't modify file download responses
                # Check if this is a file download response
                if isinstance(result, tuple) and len(result) >= 1:
                    # If it's a Flask send_file response or has a mimetype for PPTX
                    if hasattr(result[0], 'mimetype') and result[0].mimetype == 'application/vnd.openxmlformats-officedocument.presentationml.presentation':
                        logger.debug("File download detected, returning unmodified response")
                        return result
                
                # For JSON responses, add usage limits
                if isinstance(result, tuple):
                    response, status_code = result
                    if hasattr(response, 'get_json'):
                        response_data = response.get_json() or {}
                        response_data.update({
                            "usage_limits": {
                                "generations_left": usage['generations_left'],
                                "downloads_left": usage['downloads_left']
                            }
                        })
                        return jsonify(response_data), status_code
                    return result
                
                # If the result is just the response object
                if hasattr(result, 'get_json'):
                    response_data = result.get_json() or {}
                    response_data.update({
                        "usage_limits": {
                            "generations_left": usage['generations_left'],
                            "downloads_left": usage['downloads_left']
                        }
                    })
                    return jsonify(response_data)
                
                return result
                
            except Exception as e:
                logger.error(f"Error checking usage limits: {e}", exc_info=True)
                # In case of any error, still allow the request to proceed
                return f(*args, **kwargs)
                
        return decorated_function
    return decorator