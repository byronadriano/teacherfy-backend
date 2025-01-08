import os
import json
import logging
from flask import Flask, request, jsonify, send_file, redirect, url_for, session
from openai import OpenAI
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from presentation_generator import generate_presentation
from slide_processor import parse_outline_to_structured_content
from google.auth.transport import requests
from google.oauth2 import id_token
import firebase_admin
from firebase_admin import credentials, firestore

from dotenv import load_dotenv
import os
# Load environment variables from a .env file
load_dotenv()

# Try environment variable first, then file path
firebase_creds = os.environ.get("FIREBASE_CREDENTIALS")
firebase_key_path = os.environ.get("FIREBASE_KEY_PATH", "/home/site/wwwroot/firebase-adminsdk.json")

if firebase_creds:
    cred = credentials.Certificate(json.loads(firebase_creds))
elif os.path.exists(firebase_key_path):
    cred = credentials.Certificate(firebase_key_path)
else:
    raise ValueError("No Firebase credentials found!")

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

if not os.path.exists(firebase_key_path):
    raise ValueError("Firebase key file not found!")

if not firebase_admin._apps:  # Prevent reinitializing Firebase
    cred = credentials.Certificate(firebase_key_path)
    firebase_admin.initialize_app(cred)
db = firestore.client()



from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Securely fetching the secret key from Azure environment variables
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
if not app.secret_key:
    raise ValueError("FLASK_SECRET_KEY environment variable is not set!")

CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI")
SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/presentations']

# Initialize Google OAuth flow and OpenAI client
flow = Flow.from_client_config(
    {
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uris": [REDIRECT_URI],  # Keep it here, no need to repeat later
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    },
    scopes=SCOPES,
    redirect_uri=REDIRECT_URI  # Ensure it's set here once
)


try:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
except ValueError as e:
    logging.error(f"OpenAI initialization error: {e}")
    client = None

logging.basicConfig(
    level=logging.INFO,  # Change to INFO or ERROR in production
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),  # Logs to a file
        logging.StreamHandler()  # Logs to the console
    ]
)
logger = logging.getLogger(__name__)

# -------- EXAMPLE OUTLINE LOADING --------
EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), 'examples')
EXAMPLE_OUTLINES = {}
EXAMPLE_OUTLINE_DATA = {}
def load_example_outlines():
    """Load example outlines from the examples directory."""
    try:
        if not os.path.exists(EXAMPLES_DIR):
            os.makedirs(EXAMPLES_DIR)
        example_path = os.path.join(EXAMPLES_DIR, 'equivalent_fractions_outline.json')
        if not os.path.exists(example_path):
            with open(example_path, 'w', encoding='utf-8') as f:
                json.dump(EXAMPLE_OUTLINE_DATA, f, indent=2)
        
        for filename in os.listdir(EXAMPLES_DIR):
            if filename.endswith('.json'):
                with open(os.path.join(EXAMPLES_DIR, filename), 'r', encoding='utf-8') as f:
                    name = os.path.splitext(filename)[0]
                    EXAMPLE_OUTLINES[name] = json.load(f)
        logger.debug(f"Loaded {len(EXAMPLE_OUTLINES)} example outlines")
    except Exception as e:
        logger.error(f"Error loading example outlines: {e}")
        EXAMPLE_OUTLINES["fallback"] = EXAMPLE_OUTLINE_DATA  # Fallback to default

load_example_outlines()

# -------- GOOGLE SLIDES AUTH FLOW --------
@app.route('/authorize')
def authorize():
    """Initiate Google OAuth with a properly set redirect_uri."""
    try:
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )  # Removed redirect_uri from here
        session['state'] = state
        return redirect(authorization_url)
    except Exception as e:
        logger.error(f"Error during OAuth authorization: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/oauth2callback')
def oauth2callback():
    """Handle Google OAuth callback and verify user."""
    try:
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret
        }
        
        # Fetch user info
        id_info = id_token.verify_oauth2_token(
            credentials.id_token, requests.Request(), CLIENT_ID
        )
        session['user_info'] = {
            'email': id_info['email'],
            'name': id_info.get('name'),
            'picture': id_info.get('picture')
        }

        # Track login in Firestore
        db.collection('user_logins').add({
            'email': id_info['email'],
            'name': id_info.get('name'),
            'login_time': firestore.SERVER_TIMESTAMP
        })

        return redirect(url_for('dashboard'))
    except Exception as e:
        logger.error(f"Error during OAuth callback: {e}")
        return jsonify({"error": "OAuth callback failed. Check logs."}), 500

@app.route('/track_activity', methods=['POST'])
def track_activity():
    data = request.json
    logger.info(f"Received activity data: {data}")

    activity = data.get('activity')
    email = data.get('email')
    name = data.get('name')

    if not activity or not email or not name:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        doc_ref = db.collection('user_activities').document()
        activity_data = {
            'email': email,
            'name': name,
            'activity': activity,
            'timestamp': firestore.SERVER_TIMESTAMP
        }

        if activity == 'Downloaded Presentation':
            activity_data['lesson_data'] = data.get('lesson_data', {})

        doc_ref.set(activity_data)
        logger.info(f"Activity logged successfully for: {email}")
        return jsonify({"message": "Activity logged successfully"})
    except Exception as e:
        logger.error(f"Firestore write error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/dashboard')
def dashboard():
    """Display user information after login."""
    if 'user_info' in session:
        user_info = session['user_info']
        return jsonify({
            "message": "User successfully logged in",
            "user_email": user_info['email'],
            "user_name": user_info['name'],
            "profile_picture": user_info['picture']
        })
    else:
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    """Log out the user by clearing the session."""
    session.clear()
    return redirect(url_for('authorize'))


@app.route('/create_presentation')
def create_presentation():
    """Create a Google Slides presentation and return the URL."""
    if 'credentials' not in session:
        return redirect(url_for('authorize'))
    
    credentials = session['credentials']
    try:
        service = build('slides', 'v1', credentials=credentials)
        presentation = service.presentations().create(body={'title': 'New Lesson Plan'}).execute()
        return jsonify({
            'presentation_url': f"https://docs.google.com/presentation/d/{presentation['presentationId']}"
        })
    except Exception as e:
        logger.error(f"Google Slides error: {e}")
        return redirect(url_for('authorize'))  # Re-authenticate if issues arise

# -------- LESSON OUTLINE GENERATION --------
@app.route("/outline", methods=["POST", "OPTIONS"])
def get_outline():
    """Generate a lesson outline using OpenAI."""
    if request.method == "OPTIONS":
        return jsonify({"status": "OK"}), 200

    data = request.json
    logger.debug(f"Received outline request with data: {data}")

    # Check for example outline use
    is_example = (
        data.get("use_example")
        or (
            data.get("lesson_topic", "").lower().strip() == "equivalent fractions"
            and data.get("grade_level", "").lower().strip() == "4th grade"
            and data.get("subject_focus", "").lower().strip() == "math"
            and data.get("language", "").lower().strip() == "english"
        )
    )

    if is_example:
        example_data = EXAMPLE_OUTLINES.get("equivalent_fractions_outline")
        return jsonify(example_data or EXAMPLE_OUTLINE_DATA)

    # Generate a new outline using OpenAI
    if client is None:
        return jsonify({"error": "OpenAI client not initialized"}), 500

    prompt = data.get("custom_prompt")
    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    try:
        system_instructions = {
            "role": "system",
            "content": """
        You are a lesson-outline assistant. Follow this EXACT structure:

        1. Each slide starts with "Slide X:" (e.g., "Slide 1:", "Slide 2:").
        2. Next line: "Content:".
        3. Next line: "Teacher Notes:".
        4. Next line: "Visual Elements:".
        5. No extra headings or disclaimers; no "Conclusion", "Introduction", etc.

        Example of EXACT structure:

        Slide 1: Introduction to Fractions
        Content:
        - Definition: Fractions are ...
        Teacher Notes:
        - ENGAGEMENT: ...
        - ASSESSMENT: ...
        - DIFFERENTIATION: ...
        Visual Elements:
        - Picture of fractions

        (Repeat for each slide with the same headings.)

        DO NOT DEVIATE. 
            """
        }

        messages = [
            system_instructions,
            {"role": "user", "content": prompt}
        ]
        response = client.chat.completions.create(
            model="gpt-4-0125-preview",
            messages=messages
        )
        outline_text = response.choices[0].message.content.strip()
        structured_content = parse_outline_to_structured_content(outline_text)

        return jsonify({
            "messages": [outline_text],
            "structured_content": structured_content
        })
    except Exception as e:
        logging.error(f"Error generating outline: {e}")
        return jsonify({"error": str(e)}), 500

# -------- GENERATE AND DOWNLOAD .PPTX --------
@app.route("/generate", methods=["POST", "OPTIONS"])
def generate_presentation_endpoint():
    """Generate a PowerPoint presentation (.pptx) for download."""
    if request.method == "OPTIONS":
        return jsonify({"status": "OK"}), 200

    data = request.json
    outline_text = data.get('lesson_outline', '')
    structured_content = data.get('structured_content')
        
    if not structured_content:
        return jsonify({"error": "No structured content provided"}), 400

    try:
        presentation_path = generate_presentation(outline_text, structured_content)
        return send_file(
            presentation_path, 
            as_attachment=True,
            download_name="lesson_presentation.pptx",
            mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation'
        )
    except Exception as e:
        logging.error(f"Error generating presentation: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# -------- MAIN APP RUN --------
# Run with debug mode based on FLASK_ENV variable
if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_ENV", "production") != "production"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
