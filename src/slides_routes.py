from functools import wraps

from flask import Blueprint, request, jsonify, session, redirect, url_for
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from functools import wraps

from src.google_slides_generator import create_google_slides_presentation

from src.config import logger, SCOPES
slides_blueprint = Blueprint("slides_blueprint", __name__)
#
# Decorators (optional):
#
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'credentials' not in session:
            return jsonify({"error": "Authentication required", "needsAuth": True}), 401
        return f(*args, **kwargs)
    return decorated_function

def handle_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500
    return decorated_function

#
# 1. Generate Google Slides from structured content
#
@slides_blueprint.route("/generate_slides", methods=["POST", "OPTIONS"])
@handle_errors
@require_auth
def generate_slides_endpoint():
    if request.method == "OPTIONS":
        return jsonify({"status": "OK"}), 200
    
    credentials_data = session.get('credentials')
    if not credentials_data:
        return jsonify({"needsAuth": True, "error": "No credentials found in session"}), 401
    
    credentials = Credentials(
        token=credentials_data['token'],
        refresh_token=credentials_data.get('refresh_token'),
        token_uri=credentials_data['token_uri'],
        client_id=credentials_data['client_id'],
        client_secret=credentials_data['client_secret'],
        scopes=credentials_data['scopes']
    )
    
    data = request.json
    structured_content = data.get('structured_content')
    
    if not structured_content:
        return jsonify({"error": "No structured content provided"}), 400
        
    try:
        presentation_url, presentation_id = create_google_slides_presentation(
            credentials,
            structured_content
        )
        return jsonify({
            "presentation_url": presentation_url,
            "presentation_id": presentation_id
        })
    except Exception as e:
        logger.error(f"Error generating Google Slides: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

#
# 2. Create a blank Google Slides presentation
#
@slides_blueprint.route('/create_presentation')
def create_presentation_route():
    if 'credentials' not in session:
        return redirect(url_for('auth_blueprint.authorize'))
    
    credentials_data = session['credentials']
    credentials = Credentials(
        token=credentials_data['token'],
        refresh_token=credentials_data.get('refresh_token'),
        token_uri=credentials_data['token_uri'],
        client_id=credentials_data['client_id'],
        client_secret=credentials_data['client_secret'],
        scopes=SCOPES
    )
    
    try:
        service = build('slides', 'v1', credentials=credentials)
        presentation = service.presentations().create(body={'title': 'New Lesson Plan'}).execute()
        return jsonify({
            'presentation_url': f"https://docs.google.com/presentation/d/{presentation['presentationId']}"
        })
    except Exception as e:
        logger.error(f"Google Slides error: {e}", exc_info=True)
        return redirect(url_for('auth_blueprint.authorize'))
