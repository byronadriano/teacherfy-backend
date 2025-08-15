# src/slides_routes.py
from functools import wraps
from flask import Blueprint, request, jsonify, session, redirect, url_for
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config.settings import logger, SCOPES, flow

slides_blueprint = Blueprint("slides_blueprint", __name__)

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'credentials' not in session:
            return jsonify({"error": "Authentication required", "needsAuth": True}), 401
        return f(*args, **kwargs)
    return decorated_function

@slides_blueprint.route("/generate_slides", methods=["POST", "OPTIONS"])
@require_auth
def generate_slides_endpoint():
    if request.method == "OPTIONS":
        return jsonify({"status": "OK"}), 200
    
    try:
        credentials_data = session.get('credentials')
        if not credentials_data:
            return jsonify({
                "needsAuth": True,
                "error": "No credentials found in session"
            }), 401
        
        credentials = Credentials(
            token=credentials_data['token'],
            refresh_token=credentials_data.get('refresh_token'),
            token_uri=credentials_data['token_uri'],
            client_id=credentials_data['client_id'],
            client_secret=credentials_data['client_secret'],
            scopes=SCOPES
        )
        
        data = request.json
        structured_content = data.get('structured_content')
        
        if not structured_content:
            return jsonify({"error": "No structured content provided"}), 400
        
        # Use the new Google Slides handler that integrates with agent system
        from src.resource_handlers.google_slides_handler import GoogleSlidesHandler
        
        google_slides_handler = GoogleSlidesHandler(structured_content, credentials)
        presentation_url, presentation_id = google_slides_handler.generate()
        
        return jsonify({
            "presentation_url": presentation_url,
            "presentation_id": presentation_id,
            "success": True
        })
        
    except Exception as e:
        logger.error(f"Error generating Google Slides: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@slides_blueprint.route('/create_presentation')
@require_auth
def create_presentation_route():
    try:
        credentials_data = session['credentials']
        credentials = Credentials(
            token=credentials_data['token'],
            refresh_token=credentials_data.get('refresh_token'),
            token_uri=credentials_data['token_uri'],
            client_id=credentials_data['client_id'],
            client_secret=credentials_data['client_secret'],
            scopes=SCOPES
        )
        
        service = build('slides', 'v1', credentials=credentials)
        presentation = service.presentations().create(body={'title': 'New Lesson Plan'}).execute()
        
        return jsonify({
            'presentation_url': f"https://docs.google.com/presentation/d/{presentation['presentationId']}"
        })
    except Exception as e:
        logger.error(f"Error creating presentation: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500