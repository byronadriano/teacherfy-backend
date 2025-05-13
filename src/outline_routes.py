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

def get_system_instructions(resource_type="PRESENTATION"):
    """Get appropriate system instructions based on resource type"""
    resource_type = resource_type.upper()
    
    if resource_type == "PRESENTATION":
        return {
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
    elif resource_type == "LESSON_PLAN":
        return {
            "role": "system",
            "content": """
            YOU ARE A MASTER LESSON PLANNER. Your task is to create detailed lesson plans that are immediately usable by teachers. Each lesson plan should include:

            1. Clear Learning Objectives - What students will learn and be able to do by the end of the lesson
            2. Essential Materials - What the teacher needs to prepare beforehand
            3. Detailed Procedure - Step-by-step instructions for the teacher
            4. Assessment Strategies - How to evaluate student understanding
            5. Differentiation Options - How to adapt for diverse learners

            For each section of the lesson, use the exact format below:

            Section X: [Descriptive Section Title]
            Duration: [Approximate time in minutes]
            
            Content:
            - [Bullet 1: Essential information or concepts to be covered]
            - [Bullet 2: Additional key points or ideas]
            (Include 3-5 bullet points that outline the essential content)

            Procedure:
            - [Step 1: Clear instruction for what the teacher should do]
            - [Step 2: Next teaching action with specific details]
            (Include detailed steps with timing suggestions where appropriate)

            Teacher Notes:
            - ENGAGEMENT: Specific strategies to engage students with this content
            - ASSESSMENT: Concrete methods to check understanding during this section
            - DIFFERENTIATION: Specific accommodations or extensions for different learners

            Additional Directives:
            1. Each section MUST begin with "Section X:" where X is the section number
            2. The plan should flow logically from introduction to conclusion
            3. Include transitions between sections
            4. Be specific and concrete - avoid vague instructions
            5. Use grade-appropriate examples and language
            6. Ensure the plan aligns with stated learning objectives

            FINAL GOAL:
            Create a comprehensive, ready-to-use lesson plan that a teacher could implement tomorrow with minimal additional preparation.
            """
        }
    elif resource_type == "WORKSHEET":
        return {
            "role": "system",
            "content": """
            YOU ARE A MASTER EDUCATIONAL WORKSHEET CREATOR. Your task is to create engaging, educationally sound worksheets that reinforce lesson content through varied question types and activities. Each worksheet should include:

            1. Clear title and instructions
            2. A variety of question types (multiple choice, fill-in-the-blank, short answer, etc.)
            3. Age-appropriate content matching the specified grade level
            4. A logical progression from simpler to more complex questions
            5. Opportunities for creative thinking and application of concepts

            For each section of the worksheet, use the exact format below:

            Section X: [Descriptive Section Title]
            
            Instructions: [Clear, concise instructions for completing this section]
            
            Content:
            - [Question 1: Complete question text with appropriate formatting]
            - [Question 2: Complete question text with appropriate formatting]
            (Include 3-5 questions or activities in each section)

            Teacher Notes:
            - PURPOSE: Explain what skills or concepts this section assesses
            - ANSWERS: Provide answer key or evaluation criteria
            - DIFFERENTIATION: Suggest modifications for different learning needs

            Visual Elements:
            - [Describe any diagrams, charts, or spaces for drawing needed for this section]

            Additional Directives:
            1. Each section MUST begin with "Section X:" where X is the section number
            2. Include appropriate space for student responses
            3. Use grade-appropriate vocabulary and complexity
            4. Create questions that assess different cognitive levels (recall, application, analysis)
            5. Ensure all questions relate clearly to the lesson topic

            FINAL GOAL:
            Create a ready-to-use worksheet that reinforces key concepts from the lesson, engages students, and provides meaningful assessment opportunities.
            """
        }
    elif resource_type == "QUIZ":
        return {
            "role": "system",
            "content": """
            YOU ARE A MASTER ASSESSMENT DESIGNER. Your task is to create effective quizzes that accurately assess student understanding of lesson content. Each quiz should include:

            1. Clear instructions
            2. A balanced mix of question types (multiple choice, true/false, short answer)
            3. Questions that assess different cognitive levels
            4. Clear, unambiguous wording
            5. An answer key with explanations

            For each section of the quiz, use the exact format below:

            Section X: [Question Type Description]
            
            Instructions: [Clear instructions for answering this section of questions]
            
            Content:
            - [Question 1: Complete question text with all necessary components]
            - [Question 2: Complete question text with all necessary components]
            (Include appropriate number of questions based on quiz length)

            Teacher Notes:
            - ANSWERS: Correct answer with brief explanation for each question
            - SCORING: Suggested point values and grading guidance
            - ADMINISTRATION: Tips for quiz delivery and timing

            Visual Elements:
            - [Describe any diagrams, charts, or images needed for questions]

            Additional Directives:
            1. Each section MUST begin with "Section X:" where X is the section number
            2. Include a mix of difficulty levels appropriate to the grade level
            3. Avoid questions that could be answered correctly without understanding the material
            4. Ensure questions align with the learning objectives
            5. Write clear and concise questions that have unambiguous answers

            FINAL GOAL:
            Create a comprehensive assessment that accurately measures student understanding of key concepts and is ready for immediate classroom use.
            """
        }
    else:
        # Default to presentation if resource type not recognized
        logger.warning(f"Unknown resource type: {resource_type}, using PRESENTATION instructions")
        return get_system_instructions("PRESENTATION")

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
        system_instructions = get_system_instructions(resource_type)

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
                    raise ValueError(f"'{title}' has no content")
                if not item.get('teacher_notes'):
                    raise ValueError(f"'{title}' has no teacher notes")
                
                # Visual elements are optional for some resource types
                if resource_type.upper() == "PRESENTATION" and not item.get('visual_elements'):
                    logger.warning(f"Slide '{title}' has no visual elements")

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