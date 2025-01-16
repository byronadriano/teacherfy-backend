import os
import json
import logging
from flask import Flask, request, jsonify, send_file, redirect, url_for, session
from openai import OpenAI
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from presentation_generator import generate_presentation
from slide_processor import parse_outline_to_structured_content
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from google.oauth2.credentials import Credentials
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
from flask_cors import CORS
from functools import wraps

# Initialize Flask app
app = Flask(__name__)

# Enhanced logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

CORS(app, 
     resources={
         r"/*": {
             "origins": [
                 "https://teacherfy.ai",
                 "http://localhost:3000",
                 "https://teacherfy-gma6hncme7cpghda.westus-01.azurewebsites.net"
             ],
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": [
                 "Content-Type",
                 "Authorization",
                 "X-Requested-With",
                 "Accept",
                 "Origin",
                 "Access-Control-Request-Method",
                 "Access-Control-Request-Headers"
             ],
             "supports_credentials": True,
             "expose_headers": ["Content-Type", "Authorization"],
             "max_age": 3600
         }
     })

# Enhanced session configuration
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE='None',
    SESSION_COOKIE_HTTPONLY=True,
    PERMANENT_SESSION_LIFETIME=3600,  # 1 hour
    SESSION_COOKIE_DOMAIN=None  # Let Flask set this automatically
)

# Secure secret key configuration
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
if not app.secret_key:
    raise ValueError("FLASK_SECRET_KEY environment variable is not set!")

# Google OAuth configuration
CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI")
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/presentations'
]

# Initialize OAuth flow
flow = Flow.from_client_config(
    {
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uris": [REDIRECT_URI],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    },
    scopes=SCOPES
)

# Initialize OpenAI client with error handling
try:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
except ValueError as e:
    logger.error(f"OpenAI initialization error: {e}")
    client = None

# Firebase initialization with error handling
try:
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
except Exception as e:
    logger.error(f"Firebase initialization error: {e}")
    db = None

# Utility decorators
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

@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        response.headers["Access-Control-Max-Age"] = "3600"
        return response

@app.after_request
def add_cors_headers(response):
    origin = request.headers.get('Origin')
    allowed_origins = [
        "https://teacherfy.ai",
        "http://localhost:3000",
        "https://teacherfy-gma6hncme7cpghda.westus-01.azurewebsites.net"
    ]
    
    if origin in allowed_origins:
        response.headers.update({
            'Access-Control-Allow-Origin': origin,
            'Access-Control-Allow-Credentials': 'true',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With, Accept, Origin',
            'Cross-Origin-Opener-Policy': 'same-origin-allow-popups',
            'Cross-Origin-Embedder-Policy': 'require-corp'
        })
    return response

@app.route('/auth/check', methods=['GET'])
def check_auth():
    """Check if the user is authenticated and session is valid."""
    try:
        if 'credentials' not in session:
            return jsonify({
                "authenticated": False,
                "needsAuth": True
            }), 401

        credentials_data = session.get('credentials')
        if not credentials_data:
            return jsonify({
                "authenticated": False,
                "needsAuth": True
            }), 401

        # Get user info if available
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
        return jsonify({
            "authenticated": False,
            "error": str(e)
        }), 500

# Enhanced OAuth callback
@app.route('/oauth2callback')
@handle_errors
def oauth2callback():
    try:
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        
        # Store credentials securely
        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        # Verify token with additional security
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            CLIENT_ID,
            clock_skew_in_seconds=300
        )
        
        session['user_info'] = {
            'email': id_info['email'],
            'name': id_info.get('name'),
            'picture': id_info.get('picture')
        }
        
        # Log success
        logger.info(f"Successfully authenticated user: {id_info['email']}")
        
        # Track login in Firestore
        if db:
            try:
                db.collection('user_logins').add({
                    'email': id_info['email'],
                    'name': id_info.get('name'),
                    'login_time': firestore.SERVER_TIMESTAMP
                })
            except Exception as e:
                logger.error(f"Firestore login tracking error: {e}")
        
        return """
            <html><body><script>
                if (window.opener) {
                    window.opener.postMessage({
                        type: 'AUTH_SUCCESS',
                        email: '""" + id_info['email'] + """'
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

# Enhanced Google Slides generation endpoint
@app.route("/generate_slides", methods=["POST", "OPTIONS"])
@handle_errors
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
            scopes=credentials_data['scopes']
        )
        
        data = request.json
        structured_content = data.get('structured_content')
        
        if not structured_content:
            return jsonify({"error": "No structured content provided"}), 400
            
        from google_slides_generator import create_google_slides_presentation
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

# Global error handler
@app.errorhandler(Exception)
def handle_error(e):
    logger.error(f"Unhandled error: {str(e)}", exc_info=True)
    return jsonify({"error": str(e)}), 500

# Example outline data
EXAMPLE_OUTLINE_DATA = {
  "messages": [
    "Slide 1: Let's Explore Equivalent Fractions!\nContent:\n- Students will be able to recognize and create equivalent fractions in everyday situations, like sharing cookies, pizza, or our favorite Colorado trail mix.\n- Students will be able to explain why different fractions can show the same amount using pictures and numbers.\n\nTeacher Notes:\n- Begin with students sharing their experiences with fractions in their daily lives\n- Use culturally relevant examples from Denver communities\n\nVisual Elements:\n- Interactive display showing local treats divided into equivalent parts\n- Student-friendly vocabulary cards with pictures"
  ],
  "structured_content": [
    {
      "title": "Let's Explore Equivalent Fractions!",
      "layout": "TITLE_AND_CONTENT",
      "content": [
        "Today we're going on a fraction adventure!",
        "- Students will be able to recognize and create equivalent fractions in everyday situations, like sharing cookies, pizza, or our favorite Colorado trail mix",
        "- Students will be able to explain why different fractions can show the same amount using pictures and numbers",
        "- Let's start by thinking about times when we share things equally!"
      ],
      "teacher_notes": [
        "Begin with students sharing their experiences with fractions in their daily lives",
        "Use culturally relevant examples from Denver communities",
        "Encourage bilingual students to share fraction terms in their home language"
      ],
      "visual_elements": [
        "Interactive display showing local treats divided into equivalent parts",
        "Student-friendly vocabulary cards with pictures"
      ],
      "left_column": [],
      "right_column": []
    },
    {
      "title": "What Are Equivalent Fractions?",
      "layout": "TITLE_AND_CONTENT",
      "content": [
        "Let's learn our fraction vocabulary!",
        "- Imagine sharing a breakfast burrito with your friend - you can cut it in half (1/2) or into four equal pieces and take two (2/4). You get the same amount!",
        "- The top number (numerator) tells us how many pieces we have",
        "- The bottom number (denominator) tells us how many total equal pieces",
        "- When fractions show the same amount, we call them equivalent"
      ],
      "teacher_notes": [
        "Use local food examples familiar to Denver students",
        "Connect math vocabulary to real experiences",
        "Encourage students to create their own examples"
      ],
      "visual_elements": [
        "Animation of a burrito being cut into different equivalent portions",
        "Interactive fraction wall labeled in English and Spanish",
        "Hands-on fraction strips for each student"
      ],
      "left_column": [],
      "right_column": []
    },
    {
      "title": "Finding Equivalent Fractions Together",
      "layout": "TWO_COLUMNS",
      "content": [],
      "teacher_notes": [
        "Use Rocky Mountain National Park trail maps for real-world connections",
        "Encourage peer discussion in preferred language",
        "Model think-aloud strategy"
      ],
      "visual_elements": [
        "Trail map showing different fraction representations",
        "Digital manipulatives for student exploration"
      ],
      "left_column": [
        "Let's practice together!",
        "- When we multiply 1/2 by 2/2, we get 2/4",
        "- It's like taking a hiking trail that's 1/2 mile long and marking it every quarter mile - you'll have 2/4 of the trail at the same spot as 1/2!",
        "- Your turn: Try finding an equivalent fraction for 2/3"
      ],
      "right_column": [
        "Check your understanding:",
        "- Use your fraction strips to show how 1/2 = 2/4",
        "- Draw a picture to prove your answer",
        "- Share your strategy with your partner"
      ]
    },
    {
      "title": "Your Turn to Create!",
      "layout": "TITLE_AND_CONTENT",
      "content": [
        "Time to become fraction experts!",
        "- Work with your partner to create equivalent fraction cards",
        "- Use different colors to show equal parts",
        "- Challenge: Can you find three different fractions that equal 1/2?",
        "- Bonus: Create a story problem using equivalent fractions and your favorite Denver activity"
      ],
      "teacher_notes": [
        "Provide bilingual instruction cards",
        "Allow student choice in examples",
        "Support native language use in discussions"
      ],
      "visual_elements": [
        "Sample fraction cards with local themes",
        "Student workspace organization guide",
        "Visual success criteria"
      ],
      "left_column": [],
      "right_column": []
    },
    {
      "title": "Show What You Know!",
      "layout": "TITLE_AND_CONTENT",
      "content": [
        "Let's celebrate what we learned!",
        "- Create three equivalent fractions for 3/4",
        "- Draw a picture showing how you know they're equal",
        "- Write a story about using equivalent fractions in your neighborhood",
        "- Share your favorite way to remember equivalent fractions"
      ],
      "teacher_notes": [
        "Provide multiple ways to demonstrate understanding",
        "Accept explanations in English or home language",
        "Use exit ticket responses to plan next lesson"
      ],
      "visual_elements": [
        "Culturally responsive exit ticket template",
        "Digital portfolio upload guide",
        "Self-assessment checklist in multiple languages"
      ],
      "left_column": [],
      "right_column": []
    }
  ]
};

# Example outline loading
EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), 'examples')
EXAMPLE_OUTLINES = {}

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

@app.route('/authorize')
def authorize():
    """Initiate Google OAuth with a properly set redirect_uri."""
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
        return redirect(url_for('authorize'))

@app.route('/logout')
def logout():
    """Log out the user by clearing the session."""
    session.clear()
    return redirect(url_for('authorize'))

@app.route('/create_presentation')
def create_presentation_route():
    """Create a Google Slides presentation and return the URL."""
    if 'credentials' not in session:
        return redirect(url_for('authorize'))
    
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
        logger.error(f"Google Slides error: {e}")
        return redirect(url_for('authorize'))

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
        logger.error(f"Error generating outline: {e}")
        return jsonify({"error": str(e)}), 500

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
        logger.error(f"Error generating presentation: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=debug_mode)