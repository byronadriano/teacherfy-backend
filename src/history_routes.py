# src/history_routes.py - FIXED VERSION
from functools import wraps
from flask import Blueprint, request, jsonify, session
from src.config import logger
from src.db.database import get_db_cursor, get_db_connection, get_user_by_email
from psycopg2.extras import RealDictCursor  # Import this directly
import traceback
import json
from datetime import datetime, timedelta

history_blueprint = Blueprint("history_blueprint", __name__)

# Cache for anonymous session history
anonymous_history_cache = {}

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'credentials' not in session:
            return jsonify({"error": "Authentication required", "needsAuth": True}), 401
        return f(*args, **kwargs)
    return decorated_function

def format_date(timestamp):
    """Format timestamp into a user-friendly string."""
    if not timestamp:
        return "Unknown"
        
    now = datetime.now()
    if hasattr(timestamp, 'tzinfo') and timestamp.tzinfo:
        timestamp = timestamp.replace(tzinfo=None)  # Remove timezone for comparison
    
    delta = now - timestamp
    
    if delta.days == 0:
        return "Today"
    elif delta.days == 1:
        return "Yesterday"
    elif delta.days < 7:
        return f"{delta.days} days ago"
    else:
        return timestamp.strftime("%b %d, %Y")

@history_blueprint.route("/user/history", methods=["GET"])
def get_user_history():
    """Get history for the current user or session with HTTP caching."""
    try:
        # Support for HTTP cache headers
        if request.headers.get('If-None-Match'):
            # Check if the client has a fresh version based on ETag
            etag = request.headers.get('If-None-Match')
            session_id = session.get('session_id', '')
            
            # If the ETag matches the session ID (which changes when history changes),
            # return a 304 Not Modified
            if etag == session_id:
                logger.debug("Returning 304 Not Modified for history request")
                return '', 304
        
        # Get user info from session if available
        user_info = session.get('user_info', {})
        user_email = user_info.get('email')
        
        # Get IP address for anonymous users
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip_address:
            ip_address = ip_address.split(',')[0].strip()
        
        logger.info(f"Fetching history for {'user: ' + user_email if user_email else 'anonymous user: ' + ip_address}")
        
        # If user is logged in, fetch history from user_activities table
        if user_email:
            with get_db_connection() as conn:
                # FIXED: Use RealDictCursor directly
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Check which timestamp column exists
                    cursor.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_schema = 'public' 
                        AND table_name = 'user_activities'
                        AND column_name IN ('activity_time', 'created_at');
                    """)
                    timestamp_cols = [row['column_name'] for row in cursor.fetchall()]
                    
                    # Determine which timestamp column to use
                    timestamp_col = 'activity_time' if 'activity_time' in timestamp_cols else 'created_at'
                    
                    logger.debug(f"Using timestamp column: {timestamp_col}")
                    
                    # Query with the appropriate timestamp column
                    query = f"""
                        SELECT a.id, a.activity, a.lesson_data, a.{timestamp_col} as timestamp
                        FROM user_activities a
                        JOIN users u ON a.user_id = u.id
                        WHERE u.email = %s
                        ORDER BY a.{timestamp_col} DESC
                        LIMIT 10
                    """
                    
                    cursor.execute(query, (user_email,))
                    
                    results = cursor.fetchall()
                    logger.info(f"Found {len(results)} history items for user {user_email}")
                    
                    # Format the results
                    history_items = []
                    for item in results:
                        # Extract resource type from activity and lesson_data
                        resource_type = None
                        lesson_data = {}
                        
                        # FIXED: Extract resource type from activity field first
                        if item.get('activity'):
                            activity = item['activity']
                            if activity.startswith('Created '):
                                resource_type = activity.replace('Created ', '').strip()
                                logger.debug(f"📝 Extracted resource type from activity: '{resource_type}'")
                        
                        if item.get('lesson_data'):
                            if isinstance(item['lesson_data'], str):
                                try:
                                    lesson_data = json.loads(item['lesson_data'])
                                except:
                                    lesson_data = {}
                            else:
                                lesson_data = item['lesson_data']
                                
                            # Use resource type from lesson_data if not found in activity
                            if not resource_type:
                                resource_type = lesson_data.get('resourceType', 'Presentation')
                                logger.debug(f"📋 Extracted resource type from lesson_data: '{resource_type}'")
                        
                        # Ensure resource_type is a string and not None
                        if not resource_type:
                            resource_type = 'Presentation'
                            logger.warning("⚠️ No resource type found, defaulting to Presentation")
                        
                        timestamp = item.get('timestamp')
                        formatted_date = format_date(timestamp) if timestamp else "Recent"
                        
                        # Create a unique ID for the item
                        unique_id = f"{item['id']}-{resource_type}-{formatted_date}"
                        
                        # FIXED: Better title extraction
                        title = (lesson_data.get("generatedTitle") or 
                                lesson_data.get("lessonTopic") or 
                                lesson_data.get("subjectFocus") or 
                                "Untitled Lesson")
                        
                        history_items.append({
                            "id": unique_id,
                            "db_id": item["id"],
                            "title": title,
                            "types": [resource_type],  # FIXED: Store as array for consistency
                            "date": formatted_date,
                            "lessonData": lesson_data
                        })
                        
                        logger.debug(f"✅ Processed history item: {title} ({resource_type})")
                    
                    response = jsonify({
                        "history": history_items,
                        "user_authenticated": True
                    })
                    
                    # Set cache control headers
                    response.headers['Cache-Control'] = 'private, max-age=30'
                    response.headers['ETag'] = str(hash(str(history_items)))
                    return response
        
        # For anonymous users, fetch from session storage
        else:
            # Check if we have history for this IP in our cache
            cache_key = f"anon:{ip_address}"
            if cache_key in anonymous_history_cache:
                # Check if the cache is still valid (less than 30 seconds old)
                cache_time, history = anonymous_history_cache[cache_key]
                if (datetime.now() - cache_time).total_seconds() < 30:
                    logger.info(f"Using cached history for anonymous user {ip_address}")
                    return jsonify({
                        "history": history,
                        "user_authenticated": False,
                        "cache_hit": True
                    })
            
            # We store history in session for anonymous users
            history = session.get('anonymous_history', [])
            logger.info(f"Returning {len(history)} history items from session for anonymous user")
            
            # FIXED: Ensure each history item has a unique ID and proper format
            for index, item in enumerate(history):
                if 'id' not in item:
                    item['id'] = f"session-{index}"
                
                # FIXED: Ensure types is always an array
                if 'types' not in item or not isinstance(item['types'], list):
                    if item.get('lessonData', {}).get('resourceType'):
                        item['types'] = [item['lessonData']['resourceType']]
                    else:
                        item['types'] = ['Presentation']
                
                logger.debug(f"📋 Anonymous history item: {item.get('title', 'No title')} - {item.get('types', ['Unknown'])}")
            
            # Cache the result for this IP address
            anonymous_history_cache[cache_key] = (datetime.now(), history)
            
            response = jsonify({
                "history": history,
                "user_authenticated": False
            })
            
            # Set cache control headers for anonymous users
            response.headers['Cache-Control'] = 'private, max-age=30'
            response.headers['ETag'] = str(hash(str(history)))
            return response
        
    except Exception as e:
        logger.error(f"❌ Error fetching user history: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
    
@history_blueprint.route("/user/history", methods=["POST"])
def save_history_item():
    """Save a history item for the current user or session."""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Extract required data
        title = data.get("title", "Untitled Lesson")
        lesson_data = data.get("lessonData", {})
        
        # Get resource type from the correct location - check both direct field and lessonData
        resource_type = data.get("resourceType") or lesson_data.get("resourceType")
        
        # Intelligently determine resource type if not provided or if it's the default
        if not resource_type or resource_type == "PRESENTATION":
            # Check lesson data for clues about the resource type
            if lesson_data and isinstance(lesson_data, dict):
                title_lower = title.lower()
                
                # Look for worksheet indicators
                if any(keyword in title_lower for keyword in [
                    'worksheet', 'activity', 'practice', 'exercise', 'assignment'
                ]):
                    resource_type = "WORKSHEET"
                # Look for quiz/test indicators
                elif any(keyword in title_lower for keyword in [
                    'quiz', 'test', 'assessment', 'exam', 'evaluation'
                ]):
                    resource_type = "QUIZ"
                # Look for lesson plan indicators
                elif any(keyword in title_lower for keyword in [
                    'lesson plan', 'lesson', 'curriculum', 'teaching plan', 'unit plan'
                ]):
                    resource_type = "LESSON_PLAN"
                # Look for presentation indicators  
                elif any(keyword in title_lower for keyword in [
                    'presentation', 'slides', 'slideshow', 'ppt'
                ]):
                    resource_type = "PRESENTATION"
                else:
                    # Default fallback based on common patterns
                    resource_type = "PRESENTATION"
            else:
                resource_type = "PRESENTATION"
        
        logger.info(f"Saving history item: {title}, type: {resource_type}")
        
        # Get user info from session if available
        user_info = session.get('user_info', {})
        user_email = user_info.get('email')
        
        # For logged-in users, save to database
        if user_email:
            logger.info(f"Saving history for authenticated user: {user_email}")
            
            # Get user ID
            user = get_user_by_email(user_email)
            if not user:
                logger.error(f"User not found: {user_email}")
                return jsonify({"error": "User not found"}), 404
            
            user_id = user["id"]
            
            with get_db_connection() as conn:
                # FIXED: Use RealDictCursor directly
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Check which timestamp column exists
                    cursor.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_schema = 'public' 
                        AND table_name = 'user_activities'
                        AND column_name IN ('activity_time', 'created_at');
                    """)
                    timestamp_cols = [row['column_name'] for row in cursor.fetchall()]
                    
                    # Determine which timestamp column to use
                    timestamp_col = 'activity_time' if 'activity_time' in timestamp_cols else 'created_at'
                    
                    # Delete existing entries with the same title and resource type to avoid duplicates
                    cursor.execute(f"""
                        DELETE FROM user_activities 
                        WHERE user_id = %s 
                        AND lesson_data->>'lessonTopic' = %s
                        AND lesson_data->>'resourceType' = %s
                    """, (
                        user_id,
                        title,
                        resource_type
                    ))
                    
                    # Insert query with the appropriate timestamp column
                    query = f"""
                        INSERT INTO user_activities (user_id, activity, lesson_data, {timestamp_col})
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                        RETURNING id
                    """
                    
                    # Convert lesson_data to JSON string if it's not already
                    if isinstance(lesson_data, dict):
                        lesson_data_json = json.dumps(lesson_data)
                    else:
                        lesson_data_json = lesson_data
                    
                    cursor.execute(query, (
                        user_id, 
                        f"Created {resource_type}", 
                        lesson_data_json
                    ))
                    
                    result = cursor.fetchone()
                    
                    # Add this to commit the changes
                    conn.commit()
                    
                    # Clear cache for this user/IP
                    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
                    if ip_address:
                        ip_address = ip_address.split(',')[0].strip()
                    cache_key = f"anon:{ip_address}"
                    if cache_key in anonymous_history_cache:
                        del anonymous_history_cache[cache_key]
                    
                    logger.info(f"History item saved successfully with ID: {result['id'] if result else 'unknown'}")
                    
                    return jsonify({
                        "success": True,
                        "id": result["id"] if result else None,
                        "message": "History item saved successfully"
                    })
        
        # For anonymous users, save to session
        else:
            logger.info("Saving history for anonymous user")
            
            # Get IP address
            ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
            if ip_address:
                ip_address = ip_address.split(',')[0].strip()
            
            # Initialize history in session if not exists
            if 'anonymous_history' not in session:
                session['anonymous_history'] = []
            
            # Check if an item with the same title and type already exists
            existing_items = [item for item in session['anonymous_history'] 
                             if item.get('title') == title and item.get('types', [''])[0] == resource_type]
            
            if existing_items:
                # Update the existing item instead of creating a new one
                for item in existing_items:
                    item['lessonData'] = lesson_data
                    item['date'] = 'Today'  # Update the date
            else:
                # Add new item to history
                history_item = {
                    "id": f"session-{len(session['anonymous_history'])}",
                    "title": title,
                    "types": [resource_type],
                    "date": "Today",
                    "lessonData": lesson_data
                }
                
                # Insert at beginning of list
                session['anonymous_history'].insert(0, history_item)
            
            # Limit history to 10 items
            if len(session['anonymous_history']) > 10:
                session['anonymous_history'] = session['anonymous_history'][:10]
            
            # Save session
            session.modified = True
            
            # Update the cache
            cache_key = f"anon:{ip_address}"
            anonymous_history_cache[cache_key] = (datetime.now(), session['anonymous_history'])
            
            logger.info(f"History item saved to session, total items: {len(session['anonymous_history'])}")
            
            return jsonify({
                "success": True,
                "message": "History item saved to session"
            })
        
    except Exception as e:
        logger.error(f"Error saving history item: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@history_blueprint.route("/user/history/clear", methods=["POST"])
def clear_history():
    """Clear history for the current user or session."""
    try:
        # Get user info from session if available
        user_info = session.get('user_info', {})
        user_email = user_info.get('email')
        
        # For logged-in users, clear from database
        if user_email:
            logger.info(f"Clearing history for authenticated user: {user_email}")
            
            # Get user ID
            user = get_user_by_email(user_email)
            if not user:
                logger.error(f"User not found: {user_email}")
                return jsonify({"error": "User not found"}), 404
            
            user_id = user["id"]
            
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        DELETE FROM user_activities
                        WHERE user_id = %s
                    """, (user_id,))
                    
                    # Add this to commit the changes
                    conn.commit()
                    
                    return jsonify({
                        "success": True,
                        "message": "History cleared successfully"
                    })
        
        # For anonymous users, clear from session
        else:
            logger.info("Clearing history for anonymous user")
            
            # Clear history from session
            session['anonymous_history'] = []
            session.modified = True
            
            # Clear cache for this IP
            ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
            if ip_address:
                ip_address = ip_address.split(',')[0].strip()
            cache_key = f"anon:{ip_address}"
            if cache_key in anonymous_history_cache:
                del anonymous_history_cache[cache_key]
            
            return jsonify({
                "success": True,
                "message": "History cleared from session"
            })
            
    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500