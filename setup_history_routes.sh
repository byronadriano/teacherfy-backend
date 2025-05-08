#!/bin/bash
# setup_history_routes.sh

# Make sure we're in the correct directory
cd "$(dirname "$0")"

# Create the history_routes.py file
echo "Creating history_routes.py..."
cat > src/history_routes.py << 'EOL'
# src/history_routes.py
from functools import wraps
from flask import Blueprint, request, jsonify, session
from src.config import logger
from src.db.database import get_db_cursor, get_user_by_email
import traceback
import json
from datetime import datetime, timedelta

history_blueprint = Blueprint("history_blueprint", __name__)

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
    """Get history for the current user or session."""
    try:
        # Get user info from session if available
        user_info = session.get('user_info', {})
        user_email = user_info.get('email')
        
        # Get IP address for anonymous users
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip_address:
            ip_address = ip_address.split(',')[0].strip()
        
        # If user is logged in, fetch history from user_activities table
        if user_email:
            with get_db_cursor() as cursor:
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
                
                # Format the results
                history_items = []
                for item in results:
                    # Extract resource type from lesson_data if available
                    resource_type = None
                    lesson_data = {}
                    
                    if item.get('lesson_data'):
                        if isinstance(item['lesson_data'], str):
                            try:
                                lesson_data = json.loads(item['lesson_data'])
                            except:
                                lesson_data = {}
                        else:
                            lesson_data = item['lesson_data']
                            
                        resource_type = lesson_data.get('resourceType', 'PRESENTATION')
                    
                    # If resource_type is still None, extract from activity field
                    if not resource_type and item.get('activity'):
                        activity = item['activity']
                        if 'Created ' in activity:
                            resource_type = activity.replace('Created ', '')
                    
                    # Ensure resource_type is a string
                    if not resource_type:
                        resource_type = 'PRESENTATION'
                    
                    timestamp = item.get('timestamp')
                    formatted_date = format_date(timestamp) if timestamp else "Recent"
                    
                    history_items.append({
                        "id": item["id"],
                        "title": lesson_data.get("lessonTopic", "Untitled Lesson"),
                        "types": [resource_type],
                        "date": formatted_date,
                        "lessonData": lesson_data
                    })
                
                return jsonify({
                    "history": history_items,
                    "user_authenticated": True
                })
        
        # For anonymous users, fetch from session storage
        else:
            # We store history in session for anonymous users
            history = session.get('anonymous_history', [])
            
            return jsonify({
                "history": history,
                "user_authenticated": False
            })
        
    except Exception as e:
        logger.error(f"Error fetching user history: {e}")
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
        resource_type = data.get("resourceType", "PRESENTATION")
        lesson_data = data.get("lessonData", {})
        
        # Get user info from session if available
        user_info = session.get('user_info', {})
        user_email = user_info.get('email')
        
        # For logged-in users, save to database
        if user_email:
            # Get user ID
            user = get_user_by_email(user_email)
            if not user:
                return jsonify({"error": "User not found"}), 404
            
            user_id = user["id"]
            
            with get_db_cursor() as cursor:
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
                
                return jsonify({
                    "success": True,
                    "id": result["id"] if result else None,
                    "message": "History item saved successfully"
                })
        
        # For anonymous users, save to session
        else:
            # Get IP address
            ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
            if ip_address:
                ip_address = ip_address.split(',')[0].strip()
            
            # Initialize history in session if not exists
            if 'anonymous_history' not in session:
                session['anonymous_history'] = []
            
            # Add new item to history
            history_item = {
                "id": len(session['anonymous_history']) + 1,
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
            
            return jsonify({
                "success": True,
                "message": "History item saved to session"
            })
        
    except Exception as e:
        logger.error(f"Error saving history item: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
EOL

echo "✅ History routes file created successfully!"

# Update app.py to include history blueprint
echo "Updating app.py to include history blueprint..."

# First check if history_blueprint is already imported
if ! grep -q "from src.history_routes import history_blueprint" app.py; then
    # Add the import statement
    sed -i '' 's/from src.db.database import test_connection/from src.db.database import test_connection\nfrom src.history_routes import history_blueprint  # Import the new blueprint/' app.py || true
    
    # Add the blueprint registration
    sed -i '' 's/app.register_blueprint(presentation_blueprint)/app.register_blueprint(presentation_blueprint)\n    app.register_blueprint(history_blueprint)  # Register the new blueprint/' app.py || true
    
    echo "✅ app.py updated successfully!"
else
    echo "✅ History blueprint already in app.py - no changes needed."
fi

# Create the frontend history service
echo "Creating frontend history service..."
mkdir -p src/services

cat > src/services/history.js << 'EOL'
// src/services/history.js
import { httpClient } from './http';

export const historyService = {
  /**
   * Fetches user history from the server.
   * For authenticated users, it fetches history from the database.
   * For anonymous users, it returns the session-stored history.
   */
  async getUserHistory() {
    try {
      const response = await httpClient.get('/user/history');
      return response;
    } catch (error) {
      console.error('Error fetching user history:', error);
      // Return empty history on error
      return { 
        history: [], 
        user_authenticated: false,
        error: error.message
      };
    }
  },

  /**
   * Saves a history item to the server.
   * For authenticated users, it saves to the database.
   * For anonymous users, it saves to the session.
   * 
   * @param {Object} data - The history item data to save
   * @param {string} data.title - The title of the lesson
   * @param {string} data.resourceType - The type of resource
   * @param {Object} data.lessonData - The full lesson data
   */
  async saveHistoryItem(data) {
    try {
      const response = await httpClient.post('/user/history', data);
      return response;
    } catch (error) {
      console.error('Error saving history item:', error);
      throw error;
    }
  },

  /**
   * Track lesson generation for history.
   * This is a convenience method that formats the data and calls saveHistoryItem.
   * 
   * @param {Object} formState - The form state with lesson details
   * @param {Object} contentState - The content state with structured content
   */
  async trackLessonGeneration(formState, contentState) {
    try {
      const historyItem = {
        title: formState.lessonTopic || formState.subjectFocus || 'Untitled Lesson',
        resourceType: formState.resourceType || 'PRESENTATION',
        lessonData: {
          ...formState,
          structuredContent: contentState.structuredContent,
          finalOutline: contentState.finalOutline
        }
      };
      
      return await this.saveHistoryItem(historyItem);
    } catch (error) {
      console.error('Error tracking lesson generation:', error);
      // Continue even if tracking fails
      return { success: false, error: error.message };
    }
  },
  
  /**
   * Gets the history from local storage for anonymous users.
   * This is a fallback if the session storage on the server isn't available.
   */
  getLocalHistory() {
    try {
      const localHistory = localStorage.getItem('anonymous_history');
      return localHistory ? JSON.parse(localHistory) : [];
    } catch (error) {
      console.error('Error reading local history:', error);
      return [];
    }
  },
  
  /**
   * Saves history to local storage for anonymous users.
   * This is a fallback if the session storage on the server isn't available.
   * 
   * @param {Object} historyItem - The history item to save
   */
  saveLocalHistory(historyItem) {
    try {
      let history = this.getLocalHistory();
      
      // Add new item to the beginning of the array
      history.unshift(historyItem);
      
      // Limit to 10 items
      if (history.length > 10) {
        history = history.slice(0, 10);
      }
      
      localStorage.setItem('anonymous_history', JSON.stringify(history));
      return true;
    } catch (error) {
      console.error('Error saving local history:', error);
      return false;
    }
  },
  
  /**
   * Clears local history for anonymous users.
   */
  clearLocalHistory() {
    localStorage.removeItem('anonymous_history');
  }
};

export default historyService;
EOL

echo "✅ Frontend history service created successfully!"

# Add history service to services/index.js
if [ -f "src/services/index.js" ]; then
    # Check if history service is already exported
    if ! grep -q "export { historyService } from './history';" src/services/index.js; then
        # Add the export statement
        echo "Updating services/index.js..."
        echo "export { historyService } from './history'; // Add the new history service" >> src/services/index.js
        echo "✅ services/index.js updated successfully!"
    else
        echo "✅ History service already in services/index.js - no changes needed."
    fi
else
    echo "Creating services/index.js..."
    cat > src/services/index.js << 'EOL'
// src/services/index.js
export { httpClient } from './http';
export { outlineService } from './outline';
export { presentationService } from './presentation';
export { analyticsService } from './analytics';
export { historyService } from './history'; // Add the new history service
EOL
    echo "✅ services/index.js created successfully!"
fi

echo "================================================"
echo "✅ Setup completed successfully!"
echo "You can now run the migration with:"
echo "  ./run_migration.sh"
echo "and start the application with:"
echo "  python run_dev.py"
echo "================================================"