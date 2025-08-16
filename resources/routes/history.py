# Fixed history_routes.py with proper duplicate prevention
from functools import wraps
from flask import Blueprint, request, jsonify, session
from config.settings import logger
from core.database.database import get_db_cursor, get_db_connection, get_user_by_email
from psycopg2.extras import RealDictCursor
import traceback
import json
import hashlib
from datetime import datetime, timedelta

history_blueprint = Blueprint("history_blueprint", __name__)

# Cache for request deduplication (in-memory - consider Redis for production)
recent_requests = {}
anonymous_history_cache = {}

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'credentials' not in session:
            return jsonify({"error": "Authentication required", "needsAuth": True}), 401
        return f(*args, **kwargs)
    return decorated_function

def generate_content_hash(lesson_data):
    """Generate a consistent hash for lesson content to detect duplicates."""
    if not lesson_data or not isinstance(lesson_data, dict):
        return None
    
    # Create a consistent string representation for hashing
    hash_components = [
        lesson_data.get('lessonTopic', ''),
        lesson_data.get('resourceType', 'PRESENTATION'),
        lesson_data.get('subjectFocus', ''),
        lesson_data.get('gradeLevel', '')
    ]
    
    content_string = '|'.join(str(component) for component in hash_components)
    return hashlib.sha256(content_string.encode()).hexdigest()

def request_deduplication_middleware():
    """Middleware to prevent duplicate requests within a short time window."""
    if request.method != 'POST' or not request.json:
        return None
        
    # Create request fingerprint
    user_info = session.get('user_info', {})
    user_email = user_info.get('email', 'anonymous')
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    lesson_data = request.json.get('lessonData', {})
    content_hash = generate_content_hash(lesson_data)
    
    request_key = f"{user_email}:{ip_address}:{content_hash}"
    current_time = datetime.now()
    
    # Check if same request was made recently (within 30 seconds)
    if request_key in recent_requests:
        last_request_time = recent_requests[request_key]
        if (current_time - last_request_time).total_seconds() < 30:
            logger.warning(f"Duplicate request blocked: {request_key}")
            return jsonify({
                "success": True, 
                "message": "Duplicate request ignored - content already saved",
                "duplicate": True
            })
    
    # Record this request
    recent_requests[request_key] = current_time
    
    # Cleanup old requests (keep last 1000 entries)
    if len(recent_requests) > 1000:
        # Remove entries older than 5 minutes
        cutoff_time = current_time - timedelta(minutes=5)
        recent_requests.clear()  # Simple cleanup for now
    
    return None

def format_date(timestamp):
    """Format timestamp into a user-friendly string."""
    if not timestamp:
        return "Unknown"
        
    now = datetime.now()
    if hasattr(timestamp, 'tzinfo') and timestamp.tzinfo:
        timestamp = timestamp.replace(tzinfo=None)
    
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
            etag = request.headers.get('If-None-Match')
            session_id = session.get('session_id', '')
            
            if etag == session_id:
                logger.debug("Returning 304 Not Modified for history request")
                return '', 304
        
        user_info = session.get('user_info', {})
        user_email = user_info.get('email')
        
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip_address:
            ip_address = ip_address.split(',')[0].strip()
        
        logger.info(f"🔍 GET /user/history - Fetching history for {'user: ' + user_email if user_email else 'anonymous user: ' + ip_address}")
        
        if user_email:
            with get_db_connection() as conn:
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
                    timestamp_col = 'activity_time' if 'activity_time' in timestamp_cols else 'created_at'
                    
                    # Query with deduplication - get the most recent entry per content hash
                    query = f"""
                        WITH ranked_activities AS (
                            SELECT a.id, a.activity, a.lesson_data, a.{timestamp_col} as timestamp,
                                   a.content_hash,
                                   ROW_NUMBER() OVER (
                                       PARTITION BY COALESCE(a.content_hash, a.id::text)
                                       ORDER BY a.{timestamp_col} DESC
                                   ) as rn
                            FROM user_activities a
                            JOIN users u ON a.user_id = u.id
                            WHERE u.email = %s
                            AND a.lesson_data IS NOT NULL
                        )
                        SELECT id, activity, lesson_data, timestamp
                        FROM ranked_activities 
                        WHERE rn = 1
                        ORDER BY timestamp DESC
                        LIMIT 20
                    """
                    
                    cursor.execute(query, (user_email,))
                    results = cursor.fetchall()
                    logger.info(f"📦 GET /user/history - Found {len(results)} unique history items for user {user_email}")
                    
                    # Debug: Show first few results
                    if results:
                        first_item = results[0]
                        logger.debug(f"📋 Sample history item: ID {first_item['id']}, activity: {first_item['activity']}")
                        if first_item.get('lesson_data'):
                            lesson_data = first_item['lesson_data']
                            if isinstance(lesson_data, str):
                                import json
                                try:
                                    lesson_data = json.loads(lesson_data)
                                except:
                                    pass
                            title = lesson_data.get('lessonTopic') if isinstance(lesson_data, dict) else 'Unknown'
                            logger.debug(f"📋 Sample lesson title: {title}")
                    
                    # Format the results
                    history_items = []
                    for item in results:
                        resource_type = None
                        lesson_data = {}
                        
                        if item.get('activity'):
                            activity = item['activity']
                            if activity.startswith('Created '):
                                resource_type = activity.replace('Created ', '').strip()
                        
                        if item.get('lesson_data'):
                            if isinstance(item['lesson_data'], str):
                                try:
                                    lesson_data = json.loads(item['lesson_data'])
                                except:
                                    lesson_data = {}
                            else:
                                lesson_data = item['lesson_data']
                                
                            if not resource_type:
                                resource_type = lesson_data.get('resourceType', 'Presentation')
                        
                        if not resource_type:
                            resource_type = 'Presentation'
                        
                        timestamp = item.get('timestamp')
                        formatted_date = format_date(timestamp) if timestamp else "Recent"
                        
                        unique_id = f"{item['id']}-{resource_type}-{formatted_date}"
                        
                        title = (lesson_data.get("generatedTitle") or 
                                lesson_data.get("lessonTopic") or 
                                lesson_data.get("subjectFocus") or 
                                "Untitled Lesson")
                        
                        history_items.append({
                            "id": unique_id,
                            "db_id": item["id"],
                            "title": title,
                            "types": [resource_type],
                            "date": formatted_date,
                            "lessonData": lesson_data
                        })
                    
                    response = jsonify({
                        "history": history_items,
                        "user_authenticated": True
                    })
                    
                    response.headers['Cache-Control'] = 'private, max-age=30'
                    response.headers['ETag'] = str(hash(str(history_items)))
                    return response
        
        # Anonymous user logic (unchanged)
        else:
            cache_key = f"anon:{ip_address}"
            if cache_key in anonymous_history_cache:
                cache_time, history = anonymous_history_cache[cache_key]
                if (datetime.now() - cache_time).total_seconds() < 30:
                    logger.info(f"Using cached history for anonymous user {ip_address}")
                    return jsonify({
                        "history": history,
                        "user_authenticated": False,
                        "cache_hit": True
                    })
            
            history = session.get('anonymous_history', [])
            logger.info(f"Returning {len(history)} history items from session for anonymous user")
            
            for index, item in enumerate(history):
                if 'id' not in item:
                    item['id'] = f"session-{index}"
                
                if 'types' not in item or not isinstance(item['types'], list):
                    if item.get('lessonData', {}).get('resourceType'):
                        item['types'] = [item['lessonData']['resourceType']]
                    else:
                        item['types'] = ['Presentation']
            
            anonymous_history_cache[cache_key] = (datetime.now(), history)
            
            response = jsonify({
                "history": history,
                "user_authenticated": False
            })
            
            response.headers['Cache-Control'] = 'private, max-age=30'
            response.headers['ETag'] = str(hash(str(history)))
            return response
        
    except Exception as e:
        logger.error(f"❌ Error fetching user history: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@history_blueprint.route("/user/history", methods=["POST"])
def save_history_item():
    """Save a history item with proper deduplication."""
    try:
        # Check for duplicate requests first
        duplicate_check = request_deduplication_middleware()
        if duplicate_check:
            return duplicate_check
        
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        title = data.get("title", "Untitled Lesson")
        lesson_data = data.get("lessonData", {})
        
        # Get resource type
        resource_type = data.get("resourceType") or lesson_data.get("resourceType")
        
        # Handle if resource_type comes as an array
        if isinstance(resource_type, list) and resource_type:
            resource_type = resource_type[0]
            
        # Normalize to uppercase
        if resource_type:
            resource_type = resource_type.upper()
        
        # Intelligently determine resource type if not provided
        if not resource_type or resource_type == "PRESENTATION":
            title_lower = title.lower()
            
            if any(keyword in title_lower for keyword in [
                'worksheet', 'activity', 'practice', 'exercise', 'assignment'
            ]):
                resource_type = "WORKSHEET"
            elif any(keyword in title_lower for keyword in [
                'quiz', 'test', 'assessment', 'exam', 'evaluation'
            ]):
                resource_type = "QUIZ"
            elif any(keyword in title_lower for keyword in [
                'lesson plan', 'lesson', 'curriculum', 'teaching plan', 'unit plan'
            ]):
                resource_type = "LESSON_PLAN"
            else:
                resource_type = "PRESENTATION"
        
        logger.info(f"💾 POST /user/history - Saving history item: {title}, type: {resource_type}")
        
        user_info = session.get('user_info', {})
        user_email = user_info.get('email')
        logger.debug(f"🔑 User info - email: {user_email}, authenticated: {bool(user_email)}")
        
        # For logged-in users, use UPSERT logic
        if user_email:
            logger.info(f"👤 POST /user/history - Saving history for authenticated user: {user_email}")
            
            user = get_user_by_email(user_email)
            if not user:
                logger.error(f"User not found: {user_email}")
                return jsonify({"error": "User not found"}), 404
            
            user_id = user["id"]
            result = None  # Initialize result variable
            action = 'unknown'  # Initialize action variable
            
            with get_db_connection() as conn:
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
                    timestamp_col = 'activity_time' if 'activity_time' in timestamp_cols else 'created_at'
                    
                    # Generate content hash
                    content_hash = generate_content_hash(lesson_data)
                    if content_hash:
                        logger.debug(f"🔐 Generated content hash: {content_hash[:8]}... for lesson: {title}")
                    else:
                        logger.warning(f"⚠️ Content hash is NULL for lesson: {title}, lesson_data: {lesson_data}")
                        # Generate a fallback hash
                        import hashlib
                        fallback_string = f"{title}|{resource_type}|{user_email}"
                        content_hash = hashlib.sha256(fallback_string.encode()).hexdigest()
                        logger.info(f"🔄 Generated fallback hash: {content_hash[:8]}...")
                    
                    # Use UPSERT (INSERT ... ON CONFLICT) to prevent duplicates
                    lesson_data_json = json.dumps(lesson_data) if isinstance(lesson_data, dict) else lesson_data
                    
                    # Check if we have the content_hash and activity_date columns
                    cursor.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_schema = 'public' 
                        AND table_name = 'user_activities'
                        AND column_name IN ('content_hash', 'activity_date');
                    """)
                    available_cols = [row['column_name'] for row in cursor.fetchall()]
                    has_content_hash = 'content_hash' in available_cols
                    has_activity_date = 'activity_date' in available_cols
                    logger.debug(f"🗄️ Database columns - content_hash: {has_content_hash}, activity_date: {has_activity_date}")
                    
                    if has_content_hash and has_activity_date:
                        # Use the improved UPSERT with content hash and activity_date
                        # Ensure content_hash is not NULL (required for constraint)
                        if not content_hash:
                            logger.error(f"❌ Cannot use UPSERT: content_hash is NULL")
                            raise ValueError("Content hash cannot be NULL for UPSERT operation")
                            
                        upsert_query = f"""
                            INSERT INTO user_activities (user_id, activity, lesson_data, content_hash, activity_date, {timestamp_col})
                            VALUES (%s, %s, %s, %s, CURRENT_DATE, CURRENT_TIMESTAMP)
                            ON CONFLICT ON CONSTRAINT unique_user_activity_daily
                            DO UPDATE SET 
                                lesson_data = EXCLUDED.lesson_data,
                                activity = EXCLUDED.activity,
                                {timestamp_col} = CURRENT_TIMESTAMP
                            RETURNING id, 
                                CASE WHEN xmax = 0 THEN 'inserted' ELSE 'updated' END as action
                        """
                        
                        logger.debug(f"🔍 Executing UPSERT query: {upsert_query}")
                        logger.debug(f"📝 UPSERT parameters: user_id={user_id}, activity=Created {resource_type}, content_hash={content_hash[:8] if content_hash else 'NULL'}...")
                        
                        cursor.execute(upsert_query, (
                            user_id, 
                            f"Created {resource_type}", 
                            lesson_data_json,
                            content_hash
                        ))
                        
                        result = cursor.fetchone()
                        action = result.get('action', 'unknown') if result else 'unknown'
                    else:
                        # Fallback to old method if content_hash doesn't exist
                        # Check for existing entry manually
                        cursor.execute(f"""
                            SELECT id FROM user_activities 
                            WHERE user_id = %s 
                            AND lesson_data->>'lessonTopic' = %s
                            AND lesson_data->>'resourceType' = %s
                            AND {timestamp_col} > CURRENT_TIMESTAMP - INTERVAL '5 minutes'
                            LIMIT 1
                        """, (user_id, title, resource_type))
                        
                        existing = cursor.fetchone()
                        
                        if existing:
                            # Update existing entry
                            cursor.execute(f"""
                                UPDATE user_activities 
                                SET lesson_data = %s, 
                                    activity = %s,
                                    {timestamp_col} = CURRENT_TIMESTAMP
                                WHERE id = %s
                                RETURNING id
                            """, (lesson_data_json, f"Created {resource_type}", existing['id']))
                            result = cursor.fetchone()
                            action = 'updated'
                        else:
                            # Insert new entry
                            cursor.execute(f"""
                                INSERT INTO user_activities (user_id, activity, lesson_data, {timestamp_col})
                                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                                RETURNING id
                            """, (user_id, f"Created {resource_type}", lesson_data_json))
                            result = cursor.fetchone()
                            action = 'inserted'
                    
                    # result is already fetched in both code paths above
                    
                    conn.commit()
                    
                    # Clear cache
                    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
                    if ip_address:
                        ip_address = ip_address.split(',')[0].strip()
                    cache_key = f"anon:{ip_address}"
                    if cache_key in anonymous_history_cache:
                        del anonymous_history_cache[cache_key]
                    
                    # Get final action word and result info
                    action_word = action
                    result_id = result['id'] if result and 'id' in result else None
                    
                    logger.info(f"✅ POST /user/history - History item {action_word} successfully with ID: {result_id}")
                    logger.debug(f"📊 UPSERT result: {result}")
                    
                    return jsonify({
                        "success": True,
                        "id": result_id,
                        "action": action_word,
                        "message": f"History item {action_word} successfully"
                    })
        
        # Anonymous user logic (unchanged but with better duplicate detection)
        else:
            logger.info("Saving history for anonymous user")
            
            ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
            if ip_address:
                ip_address = ip_address.split(',')[0].strip()
            
            if 'anonymous_history' not in session:
                session['anonymous_history'] = []
            
            # Better duplicate detection for anonymous users
            content_hash = generate_content_hash(lesson_data)
            existing_items = [
                item for item in session['anonymous_history'] 
                if (
                    item.get('title') == title and 
                    item.get('types', [''])[0] == resource_type and
                    generate_content_hash(item.get('lessonData', {})) == content_hash
                )
            ]
            
            if existing_items:
                # Update the existing item instead of creating a new one
                for item in existing_items:
                    item['lessonData'] = lesson_data
                    item['date'] = 'Today'
                action = 'updated'
            else:
                # Add new item to history
                history_item = {
                    "id": f"session-{len(session['anonymous_history'])}",
                    "title": title,
                    "types": [resource_type],
                    "date": "Today",
                    "lessonData": lesson_data
                }
                
                session['anonymous_history'].insert(0, history_item)
                action = 'inserted'
            
            # Limit history to 10 items
            if len(session['anonymous_history']) > 10:
                session['anonymous_history'] = session['anonymous_history'][:10]
            
            session.modified = True
            
            # Update the cache
            cache_key = f"anon:{ip_address}"
            anonymous_history_cache[cache_key] = (datetime.now(), session['anonymous_history'])
            
            logger.info(f"History item {action} to session, total items: {len(session['anonymous_history'])}")
            
            return jsonify({
                "success": True,
                "action": action,
                "message": f"History item {action} to session"
            })
        
    except Exception as e:
        logger.error(f"Error saving history item: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@history_blueprint.route("/user/history/clear", methods=["POST"])
def clear_history():
    """Clear history for the current user or session."""
    try:
        user_info = session.get('user_info', {})
        user_email = user_info.get('email')
        
        if user_email:
            logger.info(f"Clearing history for authenticated user: {user_email}")
            
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
                    
                    conn.commit()
                    
                    return jsonify({
                        "success": True,
                        "message": "History cleared successfully"
                    })
        
        else:
            logger.info("Clearing history for anonymous user")
            
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