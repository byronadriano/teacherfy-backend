# src/presentation_routes.py
import os
from flask import Blueprint, request, jsonify, send_file
from src.config import logger, client
from src.slide_processor import parse_outline_to_structured_content
from src.presentation_generator import generate_presentation
from src.utils.decorators import check_usage_limits
from src.resource_handlers import PresentationHandler, LessonPlanHandler, WorksheetHandler, QuizHandler
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

        # Add resource-specific requirements based on resource type
        if resource_type.lower() == "presentation":
            requirements.extend([
                f"Number of Slides: EXACTLY {num_slides}",
                "Visual Requirements: Include clear, engaging visuals and diagrams for each slide"
            ])
        elif resource_type.lower() == "lesson_plan":
            requirements.extend([
                "Include detailed teaching procedures",
                "Include assessment strategies",
                "Include differentiation options"
            ])
        elif resource_type.lower() == "worksheet":
            requirements.extend([
                "Include a variety of question types",
                "Include space for student responses",
                "Ensure age-appropriate activities"
            ])
        elif resource_type.lower() == "quiz":
            requirements.extend([
                "Include a mix of multiple choice and short answer questions",
                "Cover key concepts from the lesson",
                "Include approximately 10 questions"
            ])

        # Build the final requirements string
        requirements_str = "\n".join(f"- {req}" for req in requirements if req)

        # Set system instructions based on resource type
        if resource_type.lower() == "presentation":
            system_content = """
            YOU ARE A MASTER CLASSROOM PRESENTATION CREATOR. Your task is to produce engaging and visually appealing slides for educational presentations.

            For each slide, use the exact format below:

            Slide X: [Engaging and Descriptive Slide Title]
            Content:
            - [Bullet 1: Present a key piece of lesson content for the students in clear, engaging, age-appropriate language.]
            - [Bullet 2: Continue with additional student-facing content such as examples, explanations, or interactive questions.]
            - [Bullet 3: Add more student-directed content to clearly convey the lesson material.]
            (Include 3-5 bullet points of actual content per slide)

            IMPORTANT GUIDELINES:
            1. Each slide MUST begin with "Slide X:" where X is the slide number
            2. The total number of slides must match the specified count exactly
            3. Use proper section headers as shown above
            4. Create a logical flow from beginning to end
            5. Make content visually engaging and suitable for the specified grade level
            6. Keep bullet points concise and readable on a slide
            """
        elif resource_type.lower() == "lesson_plan":
            system_content = """
            YOU ARE A MASTER TEACHER AND LESSON PLAN CREATOR. Your task is to produce comprehensive, ready-to-use lesson plans.

            Use the following structured format:

            LESSON PLAN: [Descriptive Title]

            OVERVIEW:
            - Grade Level:
            - Subject:
            - Duration:
            - Standards:
            - Learning Objectives:

            MATERIALS:
            - [List all required materials and resources]

            PROCEDURE:
            1. Introduction/Hook (5-10 minutes):
               - [Detailed instructions for opening the lesson]
               - ENGAGEMENT: [Specific strategies to engage students]
               - DIFFERENTIATION: [How to adapt the introduction for diverse learners]

            2. Main Activity (20-30 minutes):
               - [Step-by-step instructions for the main teaching portion]
               - ASSESSMENT: [Formative assessment strategies during instruction]
               - DIFFERENTIATION: [Modifications for different ability levels]

            3. Guided Practice (15-20 minutes):
               - [Detailed instructions for guided practice]
               - ASSESSMENT: [How to check understanding during practice]
               - DIFFERENTIATION: [Adjustments for different learning needs]

            4. Independent Practice (10-15 minutes):
               - [Instructions for independent work]
               - ASSESSMENT: [How to monitor student progress]

            5. Closure (5 minutes):
               - [Instructions for wrapping up the lesson]
               - ASSESSMENT: [Final check for understanding]

            ASSESSMENT:
            - Formative: [Specific strategies used throughout]
            - Summative: [End-of-lesson or future assessment]

            DIFFERENTIATION:
            - For struggling learners: [Specific accommodations]
            - For advanced learners: [Extension activities]
            - For ELL students: [Language supports]

            ADDITIONAL NOTES:
            - [Any other important information for the teacher]

            IMPORTANT GUIDELINES:
            1. Make the lesson plan detailed, practical, and immediately usable
            2. Include specific timing suggestions for each section
            3. Provide concrete examples, questions, and prompts
            4. Clearly indicate assessment and differentiation strategies
            5. Align all content to the specified grade level, subject, and standards
            """
        elif resource_type.lower() == "worksheet":
            system_content = """
            YOU ARE A MASTER WORKSHEET CREATOR. Your task is to produce educational worksheets that reinforce learning objectives.

            Format each worksheet as follows:

            WORKSHEET: [Descriptive Title]

            Name: _________________________________ Date: _________________

            Instructions: [Clear directions for completing the worksheet]

            PART 1: [Topic or Skill]
            1. [Question or activity with appropriate space for response]
            2. [Question or activity with appropriate space for response]
            3. [Question or activity with appropriate space for response]

            PART 2: [Topic or Skill]
            4. [Question or activity with appropriate space for response]
            5. [Question or activity with appropriate space for response]
            6. [Question or activity with appropriate space for response]

            PART 3: [Application or Challenge]
            7. [More complex question or activity with ample space for response]
            8. [More complex question or activity with ample space for response]

            IMPORTANT GUIDELINES:
            1. Create clear, age-appropriate questions and activities
            2. Include a variety of question types (multiple choice, fill-in-blank, short answer)
            3. Progress from easier to more challenging questions
            4. Provide sufficient space for student responses
            5. Align all content to the specified grade level, subject, and standards
            6. Include 8-12 questions total, organized in logical sections
            7. Make the worksheet visually clean and well-organized
            """
        elif resource_type.lower() == "quiz":
            system_content = """
            YOU ARE A MASTER ASSESSMENT CREATOR. Your task is to produce effective quizzes and tests for educational use.

            Format the quiz/test as follows:

            QUIZ/TEST: [Descriptive Title]

            Name: _________________________________ Date: _________________

            Instructions: Answer all questions to the best of your ability.

            MULTIPLE CHOICE (2 points each)
            1. [Question]
               a) [Option]
               b) [Option]
               c) [Option]
               d) [Option]

            2. [Question]
               a) [Option]
               b) [Option]
               c) [Option]
               d) [Option]

            3. [Question]
               a) [Option]
               b) [Option]
               c) [Option]
               d) [Option]

            TRUE/FALSE (1 point each)
            4. [Statement] ____________
            5. [Statement] ____________
            6. [Statement] ____________

            SHORT ANSWER (3 points each)
            7. [Question requiring brief explanation]
            _______________________________________________________________
            _______________________________________________________________

            8. [Question requiring brief explanation]
            _______________________________________________________________
            _______________________________________________________________

            EXTENDED RESPONSE (5 points)
            9. [Question requiring more detailed explanation]
            _______________________________________________________________
            _______________________________________________________________
            _______________________________________________________________
            _______________________________________________________________

            IMPORTANT GUIDELINES:
            1. Create approximately 10 questions total
            2. Include a mix of question types (multiple choice, true/false, short answer)
            3. Ensure questions assess different cognitive levels
            4. Make questions clear, specific, and free of ambiguity
            5. Align all content to the specified grade level, subject, and standards
            6. Provide adequate space for written responses
            7. Create an answer key in a separate section at the end
            """
        else:
            # Default system instructions for backward compatibility
            system_content = """
            YOU ARE A MASTER CLASSROOM CONTENT CREATOR. Your task is to produce comprehensive lesson outlines.

            For each slide, use the exact format below:

            Slide X: [Engaging and Descriptive Slide Title]
            Content:
            - [Bullet 1: Present key content in clear, engaging language.]
            - [Bullet 2: Continue with additional content, examples, or questions.]
            - [Bullet 3: Add more content to clearly convey the lesson material.]

            Teacher Notes:
            - ENGAGEMENT: Provide detailed instructions for engaging students.
            - ASSESSMENT: Describe methods to check for understanding.
            - DIFFERENTIATION: Offer strategies for adapting the lesson.

            Visual Elements:
            - List visual aids or multimedia that support the content.

            ADDITIONAL DIRECTIVES:
            1. Each slide must begin with "Slide X:" where X is the slide number
            2. Use proper section headers as shown above
            3. Use bullet points for all lists
            4. Create a logical flow from beginning to end
            5. Make content appropriate for the specified grade level
            """

        system_instructions = {
            "role": "system",
            "content": system_content
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
            3. Maintain the same number of slides/sections: {num_slides}
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
            Create a comprehensive {resource_type} with the following specifications:
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
                    slide['content'] = ["Content placeholder"]  # Add placeholder if missing
                if not slide.get('teacher_notes'):
                    slide['teacher_notes'] = ["Notes placeholder"]  # Add placeholder if missing
                if not slide.get('visual_elements'):
                    slide['visual_elements'] = []  # Empty is okay for some resource types

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

@presentation_blueprint.route("/generate", methods=["POST", "OPTIONS"])
@check_usage_limits(action_type='download')
def generate_presentation_endpoint():
    """Generate a PowerPoint presentation (.pptx) for download."""
    # Handle preflight requests
    if request.method == "OPTIONS":
        return jsonify({"status": "OK"}), 200

    # Log details about the request for debugging
    logger.info(f"Generate request received from: {request.remote_addr}")
    logger.info(f"Request headers: {dict(request.headers)}")
    
    # Get JSON data, with fallback to form data if JSON parsing fails
    try:
        data = request.get_json()
    except Exception as e:
        logger.error(f"Error parsing JSON: {e}")
        data = request.form.to_dict()  # Try form data as fallback
    
    logger.info(f"Request data structure: {type(data).__name__}")
    logger.info(f"Request data keys: {data.keys() if data else 'None'}")
    
    # Extract and validate the data
    outline_text = data.get('lesson_outline', '')
    structured_content = data.get('structured_content')
    resource_type = data.get('resource_type', 'presentation').lower()
    
    if not structured_content:
        logger.error("No structured content provided")
        return jsonify({"error": "No structured content provided"}), 400
    
    logger.info(f"Processing generate request with {len(structured_content)} slides/sections for resource type: {resource_type}")
    
    try:
        # Choose the correct handler based on resource type
        handler_map = {
            "presentation": PresentationHandler,
            "lesson_plan": LessonPlanHandler,
            "worksheet": WorksheetHandler,
            "quiz": QuizHandler
        }
        
        # Default to presentation for backward compatibility
        handler_class = handler_map.get(resource_type, PresentationHandler)
        handler = handler_class(structured_content)
        
        # Generate the appropriate resource
        resource_path = handler.generate()
        logger.info(f"Generated resource at: {resource_path}")
        
        # Verify the file exists and has content
        if not os.path.exists(resource_path):
            raise FileNotFoundError(f"Generated file not found at {resource_path}")
        
        file_size = os.path.getsize(resource_path)
        logger.info(f"Resource file size: {file_size} bytes")
        
        if file_size == 0:
            raise ValueError("Generated file is empty")
        
        # Determine MIME type based on file extension
        _, file_extension = os.path.splitext(resource_path)
        mime_types = {
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.pdf': 'application/pdf'
        }
        mime_type = mime_types.get(file_extension, 'application/octet-stream')
        
        # Prepare headers for file download
        headers = {
            'Content-Type': mime_type,
            'Content-Disposition': f'attachment; filename=lesson_{resource_type}{file_extension}',
            'Access-Control-Expose-Headers': 'Content-Disposition, Content-Type, Content-Length',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
        
        # Use Flask's send_file function to return the file
        logger.info(f"Sending file: {resource_path}")
        return send_file(
            resource_path,
            as_attachment=True,
            download_name=f"lesson_{resource_type}{file_extension}",
            mimetype=mime_type,
            etag=False,  # Disable etag to prevent caching issues
            conditional=False,  # Don't use conditional responses
            last_modified=None  # Don't include last-modified header
        ), 200, headers
        
    except Exception as e:
        logger.error(f"Error generating resource: {e}", exc_info=True)
        return jsonify({
            "error": str(e),
            "error_type": type(e).__name__,
            "stack_trace": traceback.format_exc()
        }), 500
        
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
        if response.mimetype in [
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/pdf'
        ]:
            response.headers.add('Access-Control-Expose-Headers', 'Content-Disposition')
    
    return response