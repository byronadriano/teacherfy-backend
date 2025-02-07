# src/auth_routes.py
from flask import Blueprint, request, jsonify, redirect, url_for, session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from src.config import logger, flow, CLIENT_ID
from src.db import get_user_by_email, create_user, log_user_login, log_user_activity

auth_blueprint = Blueprint("auth_blueprint", __name__)

@auth_blueprint.route('/auth/check', methods=['GET'])
def check_auth():
    """Check if the user is authenticated and session is valid."""
    try:
        if 'credentials' not in session:
            return jsonify({"authenticated": False, "needsAuth": True}), 401

        credentials_data = session.get('credentials')
        if not credentials_data:
            return jsonify({"authenticated": False, "needsAuth": True}), 401

        user_info = session.get('user_info', {})
        return jsonify({
            "authenticated": True,
            "user": {
                "email": user_info.get('email'),
                "name": user_info.get('name'),
                "picture": user_info.get('picture')
            }
        })
    except Exception as e:
        logger.error(f"Error checking auth status: {e}")
        return jsonify({"authenticated": False, "error": str(e)}), 500

@auth_blueprint.route('/oauth2callback')
def oauth2callback():
    """Handle Google's OAuth2 callback."""
    try:
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        
        # Store credentials in session
        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }

        # Verify token more securely
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            CLIENT_ID,
            clock_skew_in_seconds=300
        )

        email = id_info['email']
        name = id_info.get('name')
        picture = id_info.get('picture')

        # Store user info in session
        session['user_info'] = {
            'email': email,
            'name': name,
            'picture': picture
        }

        # Create or update user in database
        user_id = create_user(email, name, picture)
        log_user_login(user_id)
        
        logger.info(f"Successfully authenticated user: {email}")

        # Return a small HTML snippet that closes the popup window
        return """
            <html><body><script>
                if (window.opener) {
                    window.opener.postMessage({
                        type: 'AUTH_SUCCESS',
                        email: '""" + email + """'
                    }, '*');
                    window.close();
                }
            </script></body></html>
        """
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return """
            <html><body><script>
                if (window.opener) {
                    window.opener.postMessage({
                        type: 'AUTH_ERROR',
                        error: 'Authentication failed'
                    }, '*');
                    window.close();
                }
            </script></body></html>
        """

@auth_blueprint.route('/authorize')
def authorize():
    """Initiate Google OAuth with the proper redirect URI."""
    try:
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        session['state'] = state
        return redirect(authorization_url)
    except Exception as e:
        logger.error(f"Error during OAuth authorization: {e}")
        return jsonify({"error": str(e)}), 500

@auth_blueprint.route('/track_activity', methods=['POST'])
def track_activity():
    """Track user activity in database."""
    data = request.json
    logger.info(f"Received activity data: {data}")

    activity = data.get('activity')
    email = data.get('email')
    name = data.get('name')

    if not activity or not email or not name:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        user = get_user_by_email(email)
        if not user:
            return jsonify({"error": "User not found"}), 404

        lesson_data = data.get('lesson_data') if activity == 'Downloaded Presentation' else None
        log_user_activity(user['id'], activity, lesson_data)

        logger.info(f"Activity logged successfully for: {email}")
        return jsonify({"message": "Activity logged successfully"})
    except Exception as e:
        logger.error(f"Database write error: {e}")
        return jsonify({"error": str(e)}), 500

@auth_blueprint.route('/dashboard')
def dashboard():
    """Display user info after login."""
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

@auth_blueprint.route('/logout')
def logout():
    """Clear session and log out user."""
    session.clear()
    return redirect(url_for('auth_blueprint.authorize'))