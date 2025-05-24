# src/auth_routes.py - FIXED VERSION with better debugging
from flask import Blueprint, request, jsonify, redirect, url_for, session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from src.config import logger, flow, CLIENT_ID, config
from src.db import get_user_by_email, create_user, log_user_login, log_user_activity

auth_blueprint = Blueprint("auth_blueprint", __name__)

@auth_blueprint.route('/auth/check', methods=['GET'])
def check_auth():
    """Check if the user is authenticated and session is valid."""
    try:
        logger.info("🔍 DEBUG: /auth/check route called")
        logger.info(f"🔍 DEBUG: Session keys: {list(session.keys())}")
        logger.info(f"🔍 DEBUG: Session ID: {session.get('_id', 'No session ID')}")
        
        if 'credentials' not in session:
            logger.info("🔍 DEBUG: No credentials in session")
            return jsonify({
                "authenticated": False,
                "needsAuth": True
            }), 401

        credentials_data = session.get('credentials')
        if not credentials_data:
            logger.info("🔍 DEBUG: Credentials data is empty")
            return jsonify({
                "authenticated": False,
                "needsAuth": True
            }), 401

        user_info = session.get('user_info', {})
        logger.info(f"🔍 DEBUG: User info found: {user_info.get('email', 'No email')}")
        
        return jsonify({
            "authenticated": True,
            "user": {
                "email": user_info.get('email'),
                "name": user_info.get('name'),
                "picture": user_info.get('picture')
            }
        })
    except Exception as e:
        logger.error(f"❌ Error checking auth status: {e}")
        return jsonify({
            "authenticated": False,
            "error": str(e)
        }), 500

@auth_blueprint.route('/oauth2callback')
def oauth2callback():
    """Handle Google OAuth callback."""
    try:
        logger.info("🔐 OAuth callback received")
        logger.info(f"🔍 Request URL: {request.url}")
        
        # Fetch the token
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        logger.info("✅ Token fetched successfully")
        
        # Store credentials in session
        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        logger.info("💾 Credentials stored in session")

        # Verify token and get user info
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            CLIENT_ID,
            clock_skew_in_seconds=300
        )
        logger.info(f"✅ Token verified for user: {id_info.get('email')}")

        # Store user info in session
        user_info = {
            'email': id_info['email'],
            'name': id_info.get('name'),
            'picture': id_info.get('picture')
        }
        session['user_info'] = user_info
        logger.info("💾 User info stored in session")

        # Create/update user in database and log login
        try:
            user_result = create_user(user_info['email'], user_info['name'], user_info['picture'])
            user_id = user_result if isinstance(user_result, int) else user_result.get('id') if user_result else None
            
            if user_id:
                log_user_login(user_id)
                logger.info(f"✅ User login logged for ID: {user_id}")
            else:
                logger.warning("⚠️ Could not get user ID for login logging")
        except Exception as db_error:
            logger.error(f"❌ Database error during OAuth: {db_error}")
            # Continue with OAuth even if DB logging fails
        
        logger.info(f"✅ Successfully authenticated user: {user_info['email']}")
        
        # Return success message to the popup
        return """
            <html><body><script>
                console.log('OAuth success, notifying parent window');
                if (window.opener) {
                    window.opener.postMessage({
                        type: 'AUTH_SUCCESS',
                        email: '""" + user_info['email'] + """'
                    }, '*');
                    window.close();
                } else {
                    // Fallback for direct access
                    window.location.href = '/';
                }
            </script></body></html>
        """
    except Exception as e:
        logger.error(f"❌ OAuth callback error: {e}")
        return """
            <html><body><script>
                console.error('OAuth error:', '""" + str(e) + """');
                if (window.opener) {
                    window.opener.postMessage({
                        type: 'AUTH_ERROR',
                        error: 'Authentication failed: """ + str(e) + """'
                    }, '*');
                    window.close();
                } else {
                    // Fallback for direct access
                    alert('Authentication failed: """ + str(e) + """');
                    window.location.href = '/';
                }
            </script></body></html>
        """
        
@auth_blueprint.route('/authorize')
def authorize():
    """Initiate Google OAuth with the proper redirect URI."""
    try:
        logger.info("🔐 Starting OAuth authorization")
        logger.info(f"🔍 Flow redirect URI: {flow.redirect_uri}")
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        session['state'] = state
        logger.info(f"🔗 Redirecting to: {authorization_url}")
        
        return redirect(authorization_url)
    except Exception as e:
        logger.error(f"❌ Error during OAuth authorization: {e}")
        return jsonify({"error": str(e)}), 500

@auth_blueprint.route('/track_activity', methods=['POST'])
def track_activity():
    """Track user activity in database."""
    try:
        data = request.json
        logger.info(f"📊 Received activity tracking data: {data}")

        activity = data.get('activity')
        email = data.get('email')
        name = data.get('name')

        if not activity:
            return jsonify({"error": "Activity is required"}), 400

        # Try to get user from session first
        user_info = session.get('user_info', {})
        user_email = user_info.get('email') or email
        
        if not user_email:
            logger.warning("⚠️ No user email available for activity tracking")
            return jsonify({"error": "User email is required"}), 400

        try:
            user = get_user_by_email(user_email)
            if not user:
                logger.warning(f"⚠️ User not found: {user_email}")
                return jsonify({"error": "User not found"}), 404

            lesson_data = data.get('lesson_data') if activity == 'Downloaded Presentation' else None
            log_user_activity(user['id'], activity, lesson_data)

            logger.info(f"✅ Activity logged successfully for: {user_email}")
            return jsonify({"message": "Activity logged successfully"})
        except Exception as db_error:
            logger.error(f"❌ Database error in activity tracking: {db_error}")
            return jsonify({"error": "Database error"}), 500

    except Exception as e:
        logger.error(f"❌ Error in track_activity: {e}")
        return jsonify({"error": str(e)}), 500

@auth_blueprint.route('/dashboard')
def dashboard():
    """Display user info after login."""
    try:
        if 'user_info' in session:
            user_info = session['user_info']
            return jsonify({
                "message": "User successfully logged in",
                "user_email": user_info['email'],
                "user_name": user_info['name'],
                "profile_picture": user_info['picture']
            })
        else:
            return redirect(url_for('auth_blueprint.authorize'))
    except Exception as e:
        logger.error(f"❌ Dashboard error: {e}")
        return jsonify({"error": str(e)}), 500

@auth_blueprint.route('/logout')
def logout():
    """Clear session and log out user."""
    try:
        user_email = session.get('user_info', {}).get('email', 'Unknown')
        logger.info(f"🚪 Logging out user: {user_email}")
        
        session.clear()
        logger.info("✅ Session cleared")
        
        return jsonify({"message": "Logged out successfully"})
    except Exception as e:
        logger.error(f"❌ Logout error: {e}")
        return jsonify({"error": str(e)}), 500

# Add a debug route to check session
@auth_blueprint.route('/debug/session')
def debug_session():
    """Debug route to check session contents."""
    try:
        return jsonify({
            "session_keys": list(session.keys()),
            "session_id": session.get('_id', 'No session ID'),
            "has_credentials": 'credentials' in session,
            "has_user_info": 'user_info' in session,
            "user_email": session.get('user_info', {}).get('email', 'No email'),
            "session_permanent": session.permanent
        })
    except Exception as e:
        logger.error(f"❌ Debug session error: {e}")
        return jsonify({"error": str(e)}), 500