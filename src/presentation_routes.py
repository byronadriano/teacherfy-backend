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
    """Generate (or load) a comprehensive lesson outline via OpenAI."""
    if request.method == "OPTIONS":
        return jsonify({"status": "OK"}), 200

    data = request.get_json()
    logger.debug(f"Received outline request with data: {data}")
    logger.debug(f"Request headers: {dict(request.headers)}")

    # Check for an example outline using your existing criteria.
    is_example = (
        data.get("use_example")
        or (
            data.get("lesson_topic", "").lower().strip() == "equivalent fractions"
            and data.get("gradeç_level", "").lower().strip() == "4th grade"
            and data.get("subject_focus", "").lower().strip() == "math"
            and data.get("language", "").lower().strip() == "english"
        )
    )
    if is_example:
        example_data = EXAMPLE_OUTLINES.get("equivalent_fractions_outline")
        return jsonify(example_data or EXAMPLE_OUTLINE_DATA)

    if not client:
        return jsonify({"error": "OpenAI client not initialized"}), 500

    # Retrieve input fields and build a fallback custom prompt if needed.
    custom_prompt = data.get("custom_prompt", "").strip()
    selected_standards = data.get("selected_standards", [])
    standards = ", ".join(selected_standards) if selected_standards else "Not specified"

    if not custom_prompt:
        custom_prompt = (
            f"CRITICAL REQUIREMENTS:\n"
            f"THIS MUST BE A: {data.get('resource_type', 'Presentation')}\n"
            f"THIS LESSON MUST BE ABOUT: {data.get('subject_focus', 'Not specified')}\n"
            f"STANDARDS ALIGNMENT: {standards}\n"
            f"Additional Requirements: None\n"
        )

    # Build the full user prompt.
    # Note: The output must strictly follow the structure below so that our parser can detect it.
    prompt = f"""
{custom_prompt}

Create a comprehensive and engaging lesson outline in {data.get('language', 'English')} for a {data.get('grade_level', 'Not specified')} {data.get('subject_focus', 'Not specified')} lesson.
The lesson should fully cover the topic in a natural, flowing manner while ensuring that a teacher can implement it with minimal additional preparation.

**IMPORTANT:** Your output MUST follow this EXACT structure for each slide and nothing else:

Slide [number]: [Title]
Content:
- [Detailed teaching points, explanations, examples, and definitions]
Teacher Notes:
- [Detailed strategies for engagement, assessment, and differentiation]
Visual Elements:
- [Detailed suggestions for visuals, diagrams, or other resources]

Do not include any text before the first slide or after the final slide.
Ensure each slide’s sections are thorough and cover all key aspects of the topic.
    """
    logger.debug(f"Sending prompt to OpenAI: {prompt}")

    # Use system instructions that emphasize both comprehensiveness and the exact required format.
    system_instructions = {
        "role": "system",
        "content": """
You are a lesson-outline assistant. Create a comprehensive lesson outline that fully covers the topic in a logical and engaging way.
The output must be divided into slides. For each slide, use the EXACT following format:

Slide [number]: [Title]
Content:
- [Detailed teaching points, explanations, and examples]
Teacher Notes:
- [Detailed instructions for engagement, assessment, and differentiation]
Visual Elements:
- [Detailed suggestions for visuals or resources]

Do not include any extra headings, text, or commentary outside this structure.
The lesson should be complete and thorough without leaving any gaps.
        """
    }

    messages = [
        system_instructions,
        {"role": "user", "content": prompt}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4-0125-preview",
            messages=messages
        )
        outline_text = response.choices[0].message.content.strip()
        logger.debug(f"Received response from OpenAI: {outline_text}")

        structured_content = parse_outline_to_structured_content(outline_text)
        logger.debug(f"Parsed structured content: {structured_content}")

        return jsonify({
            "messages": [outline_text],
            "structured_content": structured_content
        })
    except Exception as e:
        logger.error(f"Error generating outline: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@presentation_blueprint.route("/generate", methods=["POST", "OPTIONS"])
@check_usage_limits(action_type='download')
def generate_presentation_endpoint():
    if request.method == "OPTIONS":
        return "", 204

    try:
        logger.debug(f"Generate request headers: {dict(request.headers)}")
        data = request.json
        logger.debug(f"Generate request data: {data}")

        if not data or 'structured_content' not in data:
            return jsonify({"error": "No structured content provided"}), 400

        presentation_path = generate_presentation(
            data.get('lesson_outline', ''),
            data.get('structured_content')
        )
        
        logger.debug(f"Generated presentation at: {presentation_path}")
        
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
        logger.error(f"Error generating PPTX: {str(e)}", exc_info=True)
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