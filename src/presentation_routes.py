import os
from flask import Blueprint, request, jsonify, send_file
from src.config import logger, client
from src.slide_processor import parse_outline_to_structured_content
from src.presentation_generator import generate_presentation
from src.utils.decorators import check_usage_limits
import json
import traceback

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
    # Add comprehensive logging at the start of the request
    logger.info(f"Received outline generation request: {request.method}")
    
    if request.method == "OPTIONS":
        return jsonify({"status": "OK"}), 200

    try:
        # Validate JSON request
        if not request.is_json:
            logger.error("Request is not JSON")
            return jsonify({
                "error": "Invalid request format",
                "details": "Request must be in JSON format"
            }), 400

        data = request.json
        logger.debug(f"Received outline request with data: {data}")

        # Check for regeneration request
        is_regeneration = data.get('regeneration', False)
        previous_outline = data.get('previous_outline', '')

        # Validate and set default values
        resource_type = data.get('resourceType', 'Presentation')
        subject_focus = data.get('subjectFocus', 'General Learning')
        grade_level = data.get('gradeLevel', 'Not Specified')
        language = data.get('language', 'English')
        lesson_topic = data.get('lessonTopic', 'Exploratory Lesson')
        num_slides = int(data.get('numSlides', 3))
        selected_standards = data.get('selectedStandards', [])
        custom_prompt = data.get('custom_prompt', '').strip()

        # Validate required fields
        if not all([subject_focus, grade_level, language, lesson_topic]):
            return jsonify({
                "error": "Missing required fields",
                "details": "Subject, grade level, language, and lesson topic are required."
            }), 400

        # Check for example outline
        is_example = (
            data.get("use_example") or
            (
                lesson_topic.lower().strip() == "equivalent fractions" and
                grade_level.lower().strip() == "4th grade" and
                subject_focus.lower().strip() == "math" and
                language.lower().strip() == "english"
            )
        )
        if is_example:
            example_data = EXAMPLE_OUTLINES.get("equivalent_fractions_outline")
            return jsonify(example_data or EXAMPLE_OUTLINE_DATA)

        # Validate OpenAI client
        if not client:
            return jsonify({"error": "OpenAI client not initialized"}), 500

        # Build requirements list
        requirements = [
            f"Resource Type: {resource_type}",
            f"Grade Level: {grade_level}",
            f"Subject: {subject_focus}",
            f"Topic: {lesson_topic}",
            f"Language: {language}",
            f"Standards: {', '.join(selected_standards) if selected_standards else 'General Learning Objectives'}"
        ]

        # Add resource-specific requirements
        if resource_type == "Presentation":
            requirements.extend([
                f"Number of Slides: EXACTLY {num_slides}",
                "Visual Requirements: Include clear, engaging visuals and diagrams for each slide"
            ])

        # Build the final requirements string
        requirements_str = "\n".join(f"- {req}" for req in requirements if req)

        # System instructions remain constant
        system_instructions = {
            "role": "system",
            "content": """
            YOU ARE A MASTER CLASSROOM CONTENT CREATOR. Your task is to produce lesson outlines that have two distinct parts:

            1. The student-facing "Content" section, which provides the actual lesson material that will be presented to the students. This section must use clear, engaging, and age-appropriate language and include explanations, interactive questions, or narratives that students will see. DO NOT include meta-instructions or teaching guidance in this section.

            2. The teacher-facing "Teacher Notes" section, which gives explicit, step-by-step instructions and strategies for the teacher to effectively deliver the lesson. This section may include prompts, activity instructions, assessment methods, and differentiation strategies.

            For each slide, use the exact format below:

            Slide X: [Engaging and Descriptive Slide Title]
            Content:
            - [Bullet 1: Present a key piece of lesson content directly for the students. Use language that is clear, engaging, and suitable for their age. For example, "Hoy vamos a aprender a sumar usando imágenes de manzanas."]
            - [Bullet 2: Continue with additional student-facing content such as examples, explanations, or interactive questions that the students will see.]
            - [Bullet 3: Add more student-directed content to clearly convey the lesson material.]
            (Include 3-5 bullet points that deliver the actual lesson content without giving teaching instructions.)

            Teacher Notes:
            - ENGAGEMENT: Provide detailed, step-by-step instructions for engaging students. For example, "Invite students to share what they see in the images, then ask, '¿Qué sucede cuando juntamos dos grupos de manzanas?'"
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

        # Prepare user prompt based on whether this is a regeneration request
        if is_regeneration and previous_outline:
            user_prompt = f"""
            REGENERATION REQUEST:
            Previous Outline Context:
            {previous_outline}

            NEW REQUIREMENTS:
            {requirements_str}
            
            REGENERATION INSTRUCTIONS:
            1. Review and preserve successful elements from the previous outline
            2. Update content based on the following modification request:
            {custom_prompt}
            3. Maintain the same number of slides: {num_slides}
            4. Keep the same language: {language}
            5. Ensure any new content aligns with the grade level and standards
            
            IMPORTANT:
            - Keep the successful teaching strategies from the original
            - Maintain the educational flow and progression
            - Strengthen areas mentioned in the modification request
            - Ensure all content is classroom-ready
            """
            # Log regeneration attempt
            logger.debug(f"Regeneration attempt {data.get('regenerationCount', 0) + 1}")
            logger.debug(f"Modification request: {custom_prompt}")
        else:
            # Regular outline generation prompt
            user_prompt = f"""
            Create a comprehensive lesson outline with the following specifications:
            {requirements_str}

            Additional Requirements:
            {custom_prompt}
            """

        try:
            # Make the API call
            response = client.chat.completions.create(
                model="gpt-4-0125-preview",
                messages=[
                    system_instructions,
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=4000,
                temperature=0.7
            )

            outline_text = response.choices[0].message.content.strip()
            logger.debug(f"Generated outline: {outline_text}")

            # Parse the outline into structured content
            structured_content = parse_outline_to_structured_content(outline_text)
            logger.debug(f"Structured content: {structured_content}")

            # Validate the structured content
            for slide in structured_content:
                if not slide.get('content') and not (slide.get('left_column') or slide.get('right_column')):
                    raise ValueError(f"Slide '{slide.get('title')}' has no content")
                if not slide.get('teacher_notes'):
                    raise ValueError(f"Slide '{slide.get('title')}' has no teacher notes")
                if not slide.get('visual_elements'):
                    logger.warning(f"Slide '{slide.get('title')}' has no visual elements")

            # Return the response
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
        # More detailed error logging
        logger.error(f"Unexpected error in outline generation: {str(e)}")
        logger.error(traceback.format_exc())
        
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e),
            "trace": traceback.format_exc()
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