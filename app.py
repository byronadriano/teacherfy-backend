import os
import json
import logging
from flask import Flask, request, jsonify, send_file, redirect, url_for, session
from openai import OpenAI
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from presentation_generator import generate_presentation
from slide_processor import parse_outline_to_structured_content

app = Flask(__name__)
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
            "redirect_uris": [REDIRECT_URI],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    },
    scopes=SCOPES
)

try:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
except ValueError as e:
    logging.error(f"OpenAI initialization error: {e}")
    client = None

logging.basicConfig(level=logging.DEBUG)
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
    """Initiate Google OAuth for Slides."""
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    """Handle the OAuth2 callback and store credentials."""
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    session['credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret
    }
    return redirect(url_for('create_presentation'))

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
if __name__ == "__main__":
    app.run(debug=(os.environ.get("FLASK_ENV") != "production"))

