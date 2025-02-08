import os
from flask import Blueprint, request, jsonify, send_file
from src.config import logger, client
from src.slide_processor import parse_outline_to_structured_content
from src.presentation_generator import generate_presentation
from src.utils.decorators import check_usage_limits
import json

presentation_blueprint = Blueprint("presentation_blueprint", __name__)

# Example outline data
EXAMPLE_OUTLINE_DATA = {
    "messages": [
        "Slide 1: Let's Explore Equivalent Fractions!\nContent:\n- Students ..."
    ],
    "structured_content": [
        {
            "title": "Let's Explore Equivalent Fractions!",
            "layout": "TITLE_AND_CONTENT",
            "content": [
                "Today we're going on a fraction adventure!",
                "- Students will be able to recognize and create equivalent ..."
            ],
            "teacher_notes": [
                "Begin with students sharing their experiences with fractions in their daily lives",
                "Use culturally relevant examples from Denver communities"
            ],
            "visual_elements": [
                "Interactive display showing local treats divided into equivalent parts",
                "Student-friendly vocabulary cards with pictures"
            ],
            "left_column": [],
            "right_column": []
        },
    ]
}

# Directory for storing example outlines
EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), '..', 'examples')
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
        logger.debug(f"Loaded {len(EXAMPLE_OUTLINES)} example outlines.")
    except Exception as e:
        logger.error(f"Error loading example outlines: {e}")
        EXAMPLE_OUTLINES["fallback"] = EXAMPLE_OUTLINE_DATA

@presentation_blueprint.route("/outline", methods=["POST", "OPTIONS"])
@check_usage_limits(action_type='generation')
def get_outline():
    """Generate (or load) a lesson outline via OpenAI."""
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

@presentation_blueprint.route("/generate", methods=["POST", "OPTIONS"])
@check_usage_limits(action_type='download')
def generate_presentation_endpoint():
    """Generate a PowerPoint (.pptx) for download."""
    if request.method == "OPTIONS":
        # Handle CORS preflight request
        headers = {
            'Access-Control-Allow-Origin': request.headers.get('Origin', '*'),
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Allow-Credentials': 'true',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    try:
        data = request.json
        outline_text = data.get('lesson_outline', '')
        structured_content = data.get('structured_content')
            
        if not structured_content:
            return jsonify({"error": "No structured content provided"}), 400

        presentation_path = generate_presentation(outline_text, structured_content)
        
        # Set headers for file download
        headers = {
            'Content-Type': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'Content-Disposition': 'attachment; filename=lesson_presentation.pptx',
            'Access-Control-Expose-Headers': 'Content-Disposition'
        }
        
        return send_file(
            presentation_path, 
            as_attachment=True,
            download_name="lesson_presentation.pptx",
            mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation'
        ), 200, headers
    except Exception as e:
        logger.error(f"Error generating PPTX presentation: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# Helper route to handle CORS preflight for all endpoints
@presentation_blueprint.after_request
def after_request(response):
    # Get the origin from the request
    origin = request.headers.get('Origin')
    allowed_origins = [
        'http://localhost:3000',
        'https://teacherfy.ai',
        'https://teacherfy-gma6hncme7cpghda.westus-01.azurewebsites.net'
    ]
    
    # If the origin is in our allowed list, set CORS headers
    if origin in allowed_origins:
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        
        # If this is a file download, add additional headers
        if response.mimetype == 'application/vnd.openxmlformats-officedocument.presentationml.presentation':
            response.headers.add('Access-Control-Expose-Headers', 'Content-Disposition')
    
    return response