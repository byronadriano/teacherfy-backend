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
    """Generate a comprehensive lesson outline using OpenAI."""
    if request.method == "OPTIONS":
        return jsonify({"status": "OK"}), 200

    data = request.json
    logger.debug(f"Received outline request with data: {data}")
    logger.debug(f"Request headers: {dict(request.headers)}")

    # Check for an example outline (for equivalent fractions in 4th grade math, etc.)
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

    if not client:
        return jsonify({"error": "OpenAI client not initialized"}), 500

    # Use the custom prompt provided by the frontend if available.
    custom_prompt = data.get("custom_prompt", "").strip()
    if custom_prompt:
        # Use the detailed custom prompt directly from the frontend.
        full_prompt = custom_prompt
    else:
        # If no custom prompt is provided, build a fallback prompt using other input fields.
        num_slides = int(data.get('num_slides', 5))
        logger.debug(f"Requested number of slides: {num_slides}")
        selected_standards = data.get("selected_standards", [])
        standards = ", ".join(selected_standards) if selected_standards else "Not specified"

        full_prompt = (
            f"CRITICAL REQUIREMENTS:\n"
            f"NUMBER OF SLIDES: EXACTLY {num_slides}\n"
            f"THIS MUST BE A: {data.get('resource_type', 'Presentation')}\n"
            f"THIS LESSON MUST BE ABOUT: {data.get('subject_focus', 'Not specified')}\n"
            f"STANDARDS ALIGNMENT: {standards}\n"
            f"Additional Requirements: {data.get('custom_prompt', 'None')}\n"
            "\n"
            "Follow the structure below for each slide:\n"
            "Slide [number]: [Title]\n"
            "Content:\n"
            "- [Detailed teaching points, explanations, examples, and definitions]\n"
            "Teacher Notes:\n"
            "- [Detailed strategies for engagement, assessment, and differentiation]\n"
            "Visual Elements:\n"
            "- [Detailed suggestions for visuals, diagrams, or other resources]\n"
        )

    # Append additional context to ensure that the content is actual teaching material.
    full_prompt += f"""

Create a comprehensive and engaging lesson outline in {data.get('language', 'English')} for a {data.get('grade_level', 'Not specified')} {data.get('subject_focus', 'Not specified')} lesson.
The Content section must contain actual teaching material – clear definitions, detailed explanations, and concrete examples or problems – rather than meta–instructions.
The Teacher Notes and Visual Elements sections (in English) must include specific, ready-to-use instructions.
Do not include any extra commentary or meta–instructions before the first slide or after the final slide.
"""

    logger.debug(f"Final prompt for OpenAI: {full_prompt}")

    # Update the system instructions so they reinforce the detailed instructions provided by the frontend.
    system_instructions = {
        "role": "system",
        "content": """
You are a lesson-outline assistant. Your task is to generate a complete, ready-to-use lesson outline using the exact detailed instructions provided by the user.
For each slide, include:
  - A Title.
  - A Content section that contains actual teaching material (definitions, explanations, concrete examples or problems) in the lesson language.
  - A Teacher Notes section in English with specific, actionable instructions for engagement, assessment, and differentiation.
  - A Visual Elements section in English with explicit suggestions for visuals, diagrams, or other resources.
Do not add any extraneous text or commentary outside the provided slide structure.
"""
    }

    messages = [
        system_instructions,
        {"role": "user", "content": full_prompt}
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
    """Generate a PowerPoint presentation (.pptx) for download."""
    if request.method == "OPTIONS":
        return jsonify({"status": "OK"}), 200

    data = request.json
    logger.debug(f"Generate request headers: {dict(request.headers)}")
    logger.debug(f"Generate request data: {data}")

    outline_text = data.get('lesson_outline', '')
    structured_content = data.get('structured_content')
        
    if not structured_content:
        return jsonify({"error": "No structured content provided"}), 400

    try:
        presentation_path = generate_presentation(outline_text, structured_content)
        logger.debug(f"Generated presentation at: {presentation_path}")

        # Prepare headers for file download
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
        logger.error(f"Error generating presentation: {e}", exc_info=True)
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