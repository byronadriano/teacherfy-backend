# src/outline_routes.py
import os
from flask import Blueprint, request, jsonify
from src.config import logger, client
from src.slide_processor import parse_outline_to_structured_content
from src.utils.decorators import check_usage_limits
import json
import traceback

outline_blueprint = Blueprint("outline_blueprint", __name__)

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

def get_system_prompt(resource_type="PRESENTATION"):
    """
    Get the appropriate system prompt based on resource type.
    This ensures consistent formatting for each resource type.
    """
    resource_type = resource_type.upper()
    
    if resource_type == "PRESENTATION":
        return """
        YOU ARE A MASTER CLASSROOM PRESENTATION CREATOR. Your task is to produce engaging and educationally sound slides.

        FOLLOW THIS EXACT FORMAT FOR EACH SLIDE:

        Slide X: [Clear, Engaging Title]
        Content:
        - [First bullet point of student-facing content]
        - [Second bullet point of student-facing content]
        - [Additional bullet points as needed]

        CRITICAL FORMATTING REQUIREMENTS:
        1. ALWAYS start each slide with "Slide X:" where X is the slide number
        2. ALWAYS include the exact section header: "Content:"
        3. ALWAYS use bullet points with a hyphen (-) for all list items
        4. EXACTLY match the requested number of slides
        5. Make each slide directly usable in a classroom
        6. First slide should provide an overview/objectives
        7. Last slide should include key takeaways or review points
        8. DO NOT include Teacher Notes or Visual Elements sections
        9. Keep content concise and suitable for slide display
        """
    
    elif resource_type == "LESSON_PLAN":
        return """
        YOU ARE A MASTER LESSON PLAN CREATOR. Your task is to produce comprehensive, ready-to-implement lesson plans.

        FOLLOW THIS EXACT FORMAT FOR EACH SECTION:

        Section X: [Clear, Descriptive Title]
        Duration: [Time in minutes]
        
        Content:
        - [Key concept or information to cover]
        - [Essential content for this section]
        - [Additional content points]
        
        Procedure:
        - [Specific teacher action 1]
        - [Specific teacher action 2]
        - [Additional teacher actions]
        
        Teacher Notes:
        - ENGAGEMENT: [Specific strategies to engage students]
        - ASSESSMENT: [Concrete methods to check understanding]
        - DIFFERENTIATION: [Specific accommodations for different learners]

        CRITICAL FORMATTING REQUIREMENTS:
        1. ALWAYS start each section with "Section X:" where X is the section number
        2. ALWAYS include the exact section headers: "Duration:", "Content:", "Procedure:", and "Teacher Notes:"
        3. ALWAYS use bullet points with a hyphen (-) for all list items
        4. EXACTLY match the requested number of sections
        5. Make sections follow a logical instructional sequence
        6. First section should introduce the lesson
        7. Last section should provide closure/assessment
        """
    
    elif resource_type == "WORKSHEET":
        return """
        YOU ARE A MASTER WORKSHEET CREATOR. Your task is to produce educational worksheets that reinforce key concepts.

        FOLLOW THIS EXACT FORMAT FOR EACH SECTION:

        Section X: [Clear, Descriptive Title]
        
        Instructions:
        - [Clear directions for completing this section]
        
        Content:
        - [Question or activity 1]
        - [Question or activity 2]
        - [Additional questions or activities]
        
        Teacher Notes:
        - PURPOSE: [Learning objective for this section]
        - ANSWERS: [Correct answers or evaluation criteria]
        - DIFFERENTIATION: [Modifications for different learners]

        CRITICAL FORMATTING REQUIREMENTS:
        1. ALWAYS start each section with "Section X:" where X is the section number
        2. ALWAYS include the exact section headers: "Instructions:", "Content:", and "Teacher Notes:"
        3. ALWAYS use bullet points with a hyphen (-) for all list items
        4. EXACTLY match the requested number of sections
        5. Create age-appropriate questions/activities
        6. Include a variety of question types
        7. Arrange questions from easier to more challenging
        """
    
    elif resource_type == "QUIZ":
        return """
        YOU ARE A MASTER ASSESSMENT CREATOR. Your task is to produce effective quizzes that accurately assess learning.

        FOLLOW THIS EXACT FORMAT FOR EACH SECTION:

        Section X: [Question Type Description]
        
        Content:
        - [Question 1 with all components (options for multiple choice)]
        - [Question 2 with all components]
        - [Additional questions]
        
        Answers:
        - [Answer for question 1]
        - [Answer for question 2]
        - [Additional answers]
        
        Teacher Notes:
        - SCORING: [Point values and grading guidance]
        - ADMINISTRATION: [Tips for quiz delivery and timing]

        CRITICAL FORMATTING REQUIREMENTS:
        1. ALWAYS start each section with "Section X:" where X is the section number
        2. ALWAYS include the exact section headers: "Content:", "Answers:", and "Teacher Notes:"
        3. ALWAYS use bullet points with a hyphen (-) for all list items
        4. EXACTLY match the requested number of sections
        5. Include a mix of question types
        6. Create clear, unambiguous questions
        7. Ensure questions have definite correct answers
        """
    
    else:
        # Default to presentation format if resource type not recognized
        return get_system_prompt("PRESENTATION")
    
@outline_blueprint.route("/outline", methods=["POST", "OPTIONS"])
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
        num_sections = int(data.get('numSections', 5))  # For non-presentation resources
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
        if resource_type.upper() == "PRESENTATION":
            requirements.extend([
                f"Number of Slides: EXACTLY {num_slides}",
                "Visual Requirements: Include clear, engaging visuals and diagrams for each slide"
            ])
        else:
            # For lesson plans, worksheets, and quizzes
            requirements.extend([
                f"Number of Sections: EXACTLY {num_sections}",
                f"Format: Structure as {resource_type.lower()} sections rather than slides",
                "Visual Requirements: Include clear, engaging visuals and diagrams as needed"
            ])

        # Build the final requirements string
        requirements_str = "\n".join(f"- {req}" for req in requirements if req)

        # Get system instructions based on resource type
        system_instructions = {
            "role": "system",
            "content": get_system_prompt(resource_type)
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
            3. Maintain the same number of {'slides' if resource_type.upper() == 'PRESENTATION' else 'sections'}: {num_slides if resource_type.upper() == 'PRESENTATION' else num_sections}
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
            Create a comprehensive {resource_type.lower()} outline with the following specifications:
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
            # We use the same parser for all resource types, as the format is similar enough
            structured_content = parse_outline_to_structured_content(outline_text, resource_type)
            logger.debug(f"Structured content: {structured_content}")

            # Validate the structured content
            for item in structured_content:
                title = item.get('title', '')
                if not item.get('content') and not (item.get('left_column') or item.get('right_column')):
                    item['content'] = ["Content placeholder"]  # Add placeholder if missing
                if not item.get('teacher_notes'):
                    item['teacher_notes'] = ["Notes placeholder"]  # Add placeholder if missing
                if not item.get('visual_elements'):
                    item['visual_elements'] = []  # Empty is okay for some resource types

            # Return the response
            return jsonify({
                "messages": [outline_text],
                "structured_content": structured_content,
                "resource_type": resource_type
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

# Helper route to handle CORS preflight for all endpoints
@outline_blueprint.after_request
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
    
    return response