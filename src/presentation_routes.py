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
    """Generate a lesson outline using OpenAI."""
    if request.method == "OPTIONS":
        return jsonify({"status": "OK"}), 200

    try:
        data = request.json
        logger.debug(f"Received outline request with data: {data}")

        # Check for regeneration request
        is_regeneration = data.get('regeneration', False)
        previous_outline = data.get('previous_outline', '')

        # Validate and set default values
        resource_type = data.get('resourceType', 'Presentation')
        subject_focus = data.get('subjectFocus', 'General Learning')
        grade_level = data.get('gradeLevel', 'Not Specified')
        language = data.get('language', 'Spanish')
        lesson_topic = data.get('lessonTopic', 'Exploratory Lesson')
        num_slides = int(data.get('numSlides', 3))
        selected_standards = data.get('selectedStandards', [])
        custom_prompt = data.get('custom_prompt', '').strip()

        # Check for an example outline
        is_example = (
            data.get("use_example")
            or (
                lesson_topic.lower().strip() == "equivalent fractions"
                and grade_level.lower().strip() == "4th grade"
                and subject_focus.lower().strip() == "math"
                and language.lower().strip() == "english"
            )
        )
        if is_example:
            example_data = EXAMPLE_OUTLINES.get("equivalent_fractions_outline")
            return jsonify(example_data or EXAMPLE_OUTLINE_DATA)

        # Validate OpenAI client
        if not client:
            return jsonify({"error": "OpenAI client not initialized"}), 500

        # Prepare system instructions
        system_instructions = {
            "role": "system",
            "content": """
        YOU ARE A MASTER CLASSROOM CONTENT CREATOR. Your task is to produce lesson outlines that have two distinct parts:

        1. The student-facing "Content" section, which provides the actual lesson material that will be presented to the students. This section must use clear, engaging, and age-appropriate language and include explanations, interactive questions, or narratives that students will see. DO NOT include meta-instructions or teaching guidance in this section.

        2. The teacher-facing "Teacher Notes" section, which gives explicit, step-by-step instructions and strategies for the teacher to effectively deliver the lesson. This section may include prompts, activity instructions, assessment methods, and differentiation strategies.

        For each slide, use the exact format below:

        Slide X: [Engaging and Descriptive Slide Title]
        Content:
        - [Bullet 1: Present a key piece of lesson content directly for the students. Use language that is clear, engaging, and suitable for their age. For example, “Hoy vamos a aprender a sumar usando imágenes de manzanas.”]
        - [Bullet 2: Continue with additional student-facing content such as examples, explanations, or interactive questions that the students will see.]
        - [Bullet 3: Add more student-directed content to clearly convey the lesson material.]
        (Include 3-5 bullet points that deliver the actual lesson content without giving teaching instructions.)

        Teacher Notes:
        - ENGAGEMENT: Provide detailed, step-by-step instructions for engaging students. For example, “Invite students to share what they see in the images, then ask, ‘¿Qué sucede cuando juntamos dos grupos de manzanas?’”
        - ASSESSMENT: Describe precise methods to check for understanding (e.g., ask targeted questions or use quick formative assessments).
        - DIFFERENTIATION: Offer specific strategies for adapting the lesson to meet diverse learner needs, such as modifications or extension tasks.

        Visual Elements:
        - List explicit recommendations for visual aids or multimedia (e.g., images, diagrams, animations) that support the student content on the slide.

        Additional Directives:
        1. Each slide MUST begin with "Slide X:" where X is the slide number, and the total number of slides must match the specified count exactly.
        2. The section headers "Content:", "Teacher Notes:", and "Visual Elements:" must appear exactly as shown.
        3. Use a hyphen (-) followed by a space for every bullet point.
        4. Do NOT include any extra headings (such as "Introduction" or "Conclusion"), disclaimers, or placeholder markers.
        5. Ensure that the "Content" section is purely student-facing material that presents the lesson narrative, while all teaching instructions are confined to the "Teacher Notes" section.
        6. The lesson must flow logically from one slide to the next, using concrete, real-world examples that resonate with the specified grade level.

        FINAL GOAL:
        Produce a comprehensive lesson outline that separates engaging, student-directed content from clear, actionable teacher instructions. The student content must be directly understandable and engaging, while the teacher notes guide the educator on how to deliver the lesson effectively. The outline must be ready for immediate classroom use with ZERO additional preparation.
            """
        }




        # Prepare prompt - different logic for regeneration
        if is_regeneration and previous_outline:
            full_prompt = f"""
REGENERATION REQUEST:
Previous Outline Context:
{previous_outline}

NEW REQUIREMENTS:
- Resource Type: {resource_type}
- Grade Level: {grade_level}
- Subject: {subject_focus}
- Lesson Topic: {lesson_topic}
- Language: {language}
- Number of Slides: EXACTLY {num_slides}
- Standards Alignment: {', '.join(selected_standards) if selected_standards else 'Previous Standards'}

REGENERATION INSTRUCTIONS:
1. Carefully review the previous outline
2. Incorporate new requirements while maintaining core educational objectives
3. Ensure coherence and educational continuity
4. Provide a refined, improved lesson outline

SPECIFIC MODIFICATION GUIDANCE:
{custom_prompt}
"""
        else:
            # Original outline generation prompt
            full_prompt = f"""
Create a comprehensive lesson outline with the following specifications:
- Resource Type: {resource_type}
- Grade Level: {grade_level}
- Subject: {subject_focus}
- Lesson Topic: {lesson_topic}
- Language: {language}
- Number of Slides: EXACTLY {num_slides}
- Standards Alignment: {', '.join(selected_standards) if selected_standards else 'General Learning Objectives'}

Additional Requirements:
{custom_prompt}
"""

        # Prepare messages for OpenAI
        messages = [
            system_instructions,
            {"role": "user", "content": full_prompt}
        ]

        try:
            response = client.chat.completions.create(
                model="gpt-4-0125-preview",
                messages=messages,
                max_tokens=4000,
                temperature=0.7
            )

            outline_text = response.choices[0].message.content.strip()
            logger.debug(f"Generated outline: {outline_text}")

            structured_content = parse_outline_to_structured_content(outline_text)
            logger.debug(f"Structured content: {structured_content}")

            return jsonify({
                "messages": [outline_text],
                "structured_content": structured_content
            })

        except Exception as ai_error:
            logger.error(f"OpenAI API error: {ai_error}", exc_info=True)
            return jsonify({
                "error": "Failed to generate outline",
                "details": str(ai_error)
            }), 500

    except Exception as e:
        logger.error(f"Unexpected error in outline generation: {e}", exc_info=True)
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500 
        
        
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