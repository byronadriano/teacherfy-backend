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
from google.oauth2.credentials import Credentials  # <-- Added Import
import firebase_admin
from firebase_admin import credentials, firestore

from dotenv import load_dotenv
import os

from flask_cors import CORS

app = Flask(__name__)
# CORS(app)  # Enable CORS for all routes?/
# Update CORS configuration
# Remove this line
# CORS(app)  # Enable CORS for all routes?/

# Update CORS configuration
CORS(app, 
     resources={
         r"/*": {
             "origins": ["https://teacherfy.ai", "http://localhost:3000"],
             "methods": ["GET", "POST", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization"],
             "supports_credentials": True,
             "expose_headers": ["Content-Type", "Authorization"]
         }
     })

# Update the after_request function
@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    if origin in ["https://teacherfy.ai", "http://localhost:3000"]:
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Add these near the top of app.py with other configurations
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE='None',
    SESSION_COOKIE_DOMAIN='.teacherfy.ai'  # Adjust based on your domain
)

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


# Securely fetching the secret key from environment variables
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
if not app.secret_key:
    raise ValueError("FLASK_SECRET_KEY environment variable is not set!")

CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI")
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/presentations'
]

# Initialize Google OAuth flow and OpenAI client
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
    scopes=SCOPES,
    redirect_uri=REDIRECT_URI  # Ensure it's set here once
)

try:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
except ValueError as e:
    logging.error(f"OpenAI initialization error: {e}")
    client = None

logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for detailed logs
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
        )
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
            credentials.id_token, google_requests.Request(), CLIENT_ID
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

        # Return HTML that closes the popup and messages the parent
        return """
            <html>
                <body>
                    <script>
                        window.close();
                    </script>
                </body>
            </html>
        """
    except Exception as e:
        logger.error(f"Error during OAuth callback: {e}")
        return """
            <html>
                <body>
                    <script>
                        window.close();
                    </script>
                </body>
            </html>
        """
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
        logger.error(f"Error generating outline: {e}")
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
        logger.error(f"Error generating presentation: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# -------- GENERATE GOOGLE SLIDES --------
from google_slides_generator import create_google_slides_presentation

@app.route("/generate_slides", methods=["POST", "OPTIONS"])
def generate_slides_endpoint():
    """Generate a Google Slides presentation and return the URL."""
    if request.method == "OPTIONS":
        return jsonify({"status": "OK"}), 200

    if 'credentials' not in session:
        return redirect(url_for('authorize'))
    
    data = request.json
    structured_content = data.get('structured_content')
    
    if not structured_content:
        return jsonify({"error": "No structured content provided"}), 400

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
        # Refresh credentials if expired
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(google_requests.Request())
            # Update session with new token
            session['credentials']['token'] = credentials.token

        # Use the separate module to create the presentation
        presentation_url, presentation_id = create_google_slides_presentation(credentials, structured_content)
        
        # Log the creation activity in Firestore
        user_info = session.get('user_info', {})
        db.collection('user_activities').add({
            'email': user_info.get('email'),
            'name': user_info.get('name'),
            'activity': 'Created Google Slides Presentation',
            'presentation_id': presentation_id,
            'presentation_url': presentation_url,
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        
        return jsonify({
            'presentation_url': presentation_url
        })
    except Exception as e:
        logger.error(f"Error generating Google Slides presentation: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# -------- MAIN APP RUN --------
# Run with debug mode based on FLASK_ENV variable
if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_ENV", "production") != "production"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
