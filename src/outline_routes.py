# src/outline_routes.py - UNIFIED and CLEAN version
import os
import re
from flask import Blueprint, request, jsonify
from src.config import logger, client
from src.utils.decorators import check_usage_limits
import json
import traceback

outline_blueprint = Blueprint("outline_blueprint", __name__)

# Clean example data with new structure
EXAMPLE_OUTLINE_DATA = {
    "title": "Equivalent Fractions Lesson",
    "messages": [
        """Slide 1: Let's Explore Equivalent Fractions!
Content:
- Students will be able to recognize and create equivalent fractions in everyday situations, like sharing cookies, pizza, or our favorite Colorado trail mix
- Students will be able to explain why different fractions can show the same amount using pictures and numbers

Slide 2: What Are Equivalent Fractions?  
Content:
- Let's learn our fraction vocabulary!
- Imagine sharing a breakfast burrito with your friend - you can cut it in half (1/2) or into four equal pieces and take two (2/4). You get the same amount!
- The top number (numerator) tells us how many pieces we have
- The bottom number (denominator) tells us how many total equal pieces
- When fractions show the same amount, we call them equivalent"""
    ],
    "structured_content": [
        {
            "title": "Let's Explore Equivalent Fractions!",
            "layout": "TITLE_AND_CONTENT",
            "content": [
                "Students will be able to recognize and create equivalent fractions in everyday situations, like sharing cookies, pizza, or our favorite Colorado trail mix",
                "Students will be able to explain why different fractions can show the same amount using pictures and numbers"
            ]
        },
        {
            "title": "What Are Equivalent Fractions?",
            "layout": "TITLE_AND_CONTENT", 
            "content": [
                "Let's learn our fraction vocabulary!",
                "Imagine sharing a breakfast burrito with your friend - you can cut it in half (1/2) or into four equal pieces and take two (2/4). You get the same amount!",
                "The top number (numerator) tells us how many pieces we have",
                "The bottom number (denominator) tells us how many total equal pieces",
                "When fractions show the same amount, we call them equivalent"
            ]
        }
    ]
}

def generate_outline_title(form_data, structured_content=None):
    """Generate a meaningful title for the outline based on form data and content."""
    try:
        # Extract key information
        lesson_topic = form_data.get('lessonTopic', '').strip()
        subject_focus = form_data.get('subjectFocus', '').strip()
        grade_level = form_data.get('gradeLevel', '').strip()
        resource_type = form_data.get('resourceType', 'Lesson').strip()
        
        # Priority 1: Use lesson topic if available and meaningful
        if lesson_topic and lesson_topic.lower() not in ['general learning', 'exploratory lesson']:
            title = lesson_topic
            
            # Add resource type context if not already implied
            if not any(word in title.lower() for word in ['lesson', 'presentation', 'quiz', 'worksheet']):
                if resource_type.lower() == 'presentation':
                    title = f"{title} Presentation"
                elif resource_type.lower() in ['quiz', 'test']:
                    title = f"{title} Quiz"
                elif resource_type.lower() == 'worksheet':
                    title = f"{title} Worksheet"
                elif 'lesson' in resource_type.lower():
                    title = f"{title} Lesson Plan"
                else:
                    title = f"{title} {resource_type}"
            
            return title
        
        # Priority 2: Combine subject and grade level
        if subject_focus and grade_level:
            clean_grade = grade_level.replace('grade', '').replace('Grade', '').strip()
            if clean_grade.lower() == 'kindergarten':
                clean_grade = 'Kindergarten'
            elif clean_grade.endswith(('st', 'nd', 'rd', 'th')):
                clean_grade = f"Grade {clean_grade}"
            
            base_title = f"{clean_grade} {subject_focus}"
            
            if resource_type.lower() == 'presentation':
                title = f"{base_title} Presentation"
            elif resource_type.lower() in ['quiz', 'test']:
                title = f"{base_title} Quiz"
            elif resource_type.lower() == 'worksheet':
                title = f"{base_title} Worksheet"
            elif 'lesson' in resource_type.lower():
                title = f"{base_title} Lesson Plan"
            else:
                title = f"{base_title} {resource_type}"
                
            return title
        
        # Priority 3: Try to extract title from first slide/section
        if structured_content and len(structured_content) > 0:
            first_slide_title = structured_content[0].get('title', '').strip()
            if first_slide_title and not first_slide_title.lower().startswith(('slide 1', 'section 1')):
                clean_title = re.sub(r'^(Slide \d+:|Section \d+:)\s*', '', first_slide_title, flags=re.IGNORECASE)
                return clean_title.strip()
        
        # Fallback based on available information
        if subject_focus:
            if resource_type.lower() == 'presentation':
                return f"{subject_focus} Presentation"
            elif resource_type.lower() in ['quiz', 'test']:
                return f"{subject_focus} Quiz"
            elif resource_type.lower() == 'worksheet':
                return f"{subject_focus} Worksheet"
            elif 'lesson' in resource_type.lower():
                return f"{subject_focus} Lesson Plan"
            else:
                return f"{subject_focus} {resource_type}"
        
        # Final fallback
        return f"Educational {resource_type}"
            
    except Exception as e:
        logger.error(f"Error generating outline title: {e}")
        return "Educational Resource"

def get_system_prompt(resource_type="PRESENTATION"):
    """Get the appropriate system prompt based on resource type."""
    normalized_type = resource_type.upper() if resource_type else "PRESENTATION"
    
    # Handle various formats of resource types
    if "QUIZ" in normalized_type or "TEST" in normalized_type:
        normalized_type = "QUIZ"
    elif "LESSON" in normalized_type and "PLAN" in normalized_type:
        normalized_type = "LESSON_PLAN"
    elif "WORKSHEET" in normalized_type or "ACTIVITY" in normalized_type:
        normalized_type = "WORKSHEET"
    elif "PRESENTATION" in normalized_type or "SLIDE" in normalized_type:
        normalized_type = "PRESENTATION"
    
    if normalized_type == "QUIZ":
        return """
        YOU ARE A MASTER QUIZ AND TEST CREATOR. Your task is to produce educational assessments.

        FOLLOW THIS EXACT FORMAT FOR EACH SECTION:

        Section X: [Clear, Descriptive Title]
        Content:
        - [Question 1 with complete wording]
        - [Question 2 with complete wording]
        - [Additional questions as needed]

        CRITICAL FORMATTING REQUIREMENTS:
        1. ALWAYS start each section with "Section X:" where X is the section number
        2. ALWAYS include the exact section header: "Content:"
        3. ALWAYS use bullet points with a hyphen (-) for all list items
        4. Create clear, unambiguous questions
        5. Make questions appropriate for the grade level
        6. Include a variety of question types (multiple choice, short answer, etc.)
        """
    
    elif normalized_type == "WORKSHEET":
        return """
        YOU ARE A MASTER WORKSHEET CREATOR. Your task is to produce educational worksheets that reinforce key concepts.

        FOLLOW THIS EXACT FORMAT FOR EACH SECTION:

        Section X: [Clear, Descriptive Title]
        Content:
        - [Question or activity 1]
        - [Question or activity 2]
        - [Additional questions or activities]

        CRITICAL FORMATTING REQUIREMENTS:
        1. ALWAYS start each section with "Section X:" where X is the section number
        2. ALWAYS include the exact section header: "Content:"
        3. ALWAYS use bullet points with a hyphen (-) for all list items
        4. Create age-appropriate questions/activities
        5. Include a variety of question types
        6. Arrange questions from easier to more challenging
        """
    
    elif normalized_type == "LESSON_PLAN":
        return """
        YOU ARE A MASTER LESSON PLAN CREATOR. Your task is to produce comprehensive, ready-to-implement lesson plans.

        FOLLOW THIS EXACT FORMAT FOR EACH SECTION:

        Section X: [Clear, Descriptive Title]
        Content:
        - [Key concept or information to cover]
        - [Essential content for this section]
        - [Additional content points]

        CRITICAL FORMATTING REQUIREMENTS:
        1. ALWAYS start each section with "Section X:" where X is the section number
        2. ALWAYS include the exact section header: "Content:"
        3. ALWAYS use bullet points with a hyphen (-) for all list items
        4. Make sections follow a logical instructional sequence
        5. First section should introduce the lesson
        6. Last section should provide closure/assessment
        """
    
    else:
        # Default to presentation format
        return """
        YOU ARE A MASTER CLASSROOM PRESENTATION CREATOR. Your task is to create actual slide content for teachers to present directly to students - NOT instructions about what to teach.

        FOLLOW THIS EXACT FORMAT FOR EACH SLIDE:

        Slide X: [Engaging and Descriptive Slide Title]
        Content:
        - [Actual content for students to see and learn from - NOT teacher instructions]
        - [Clear explanation, definition, or concept presented in student-friendly language]
        - [Example, illustration, or application of the concept]
        - [Question for students or key point to remember]
        - [Summary or connection to next idea if needed]

        CRITICAL FORMATTING REQUIREMENTS:
        1. ALWAYS start each slide with "Slide X:" where X is the slide number
        2. ALWAYS include the "Content:" section header
        3. ALWAYS use bullet points with a hyphen (-) for all list items
        4. EXACTLY match the requested number of slides
        5. Write DIRECT TEACHING CONTENT that would appear on actual slides, NOT meta-instructions
        6. DO NOT use phrases like "Activity:", "Visual:", "Explain:", "Introduce:", etc.
        7. First slide should be an introduction with clear learning objectives
        8. Last slide should include key takeaways or review points
        9. Write as if speaking directly to students, not about what teachers should do
        
        EXAMPLE OF CORRECT FORMAT:
        
        Slide 1: Understanding Fractions
        Content:
        - A fraction represents a part of a whole
        - The numerator (top number) tells us how many parts we have
        - The denominator (bottom number) tells us the total number of equal parts
        - Fractions are everywhere in daily life: half a pizza, quarter of an hour
        - Let's explore how fractions help us understand the world around us
        """
        
def parse_outline_to_clean_structure(outline_text, resource_type="PRESENTATION"):
    """Parse outline text into clean, consistent structure for all resource types."""
    logger.info(f"Parsing outline for resource type: {resource_type}")
    
    # Determine section/slide pattern based on resource type
    if resource_type.upper() == "PRESENTATION":
        section_pattern = r"Slide (\d+):\s*(.*)"
        section_word = "Slide"
    else:
        section_pattern = r"Section (\d+):\s*(.*)"
        section_word = "Section"
    
    # Split by section headers
    sections = []
    current_section = None
    
    lines = outline_text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this is a section/slide header
        match = re.match(section_pattern, line)
        if match:
            # Save previous section
            if current_section:
                sections.append(current_section)
            
            # Start new section
            section_num = match.group(1)
            section_title = match.group(2).strip()
            current_section = {
                "title": section_title,
                "layout": "TITLE_AND_CONTENT",
                "content": []
            }
        elif line.lower() == "content:":
            # Skip content headers
            continue
        elif line.startswith('-') or line.startswith('•'):
            # This is content
            if current_section:
                clean_content = line.lstrip('-•').strip()
                if clean_content:
                    current_section["content"].append(clean_content)
        elif current_section and line:
            # Any other non-empty line goes to content
            current_section["content"].append(line)
    
    # Don't forget the last section
    if current_section:
        sections.append(current_section)
    
    # If no sections found, create a fallback
    if not sections:
        sections.append({
            "title": "Generated Content",
            "layout": "TITLE_AND_CONTENT",
            "content": [line.strip() for line in lines if line.strip()]
        })
    
    logger.info(f"Successfully parsed {len(sections)} sections for {resource_type}")
    return sections

@outline_blueprint.route("/outline", methods=["POST", "OPTIONS"])
@check_usage_limits(action_type='generation')
def get_outline():
    """Generate a lesson outline using OpenAI - UNIFIED ENDPOINT"""
    logger.info(f"Received outline generation request: {request.method}")
    
    if request.method == "OPTIONS":
        return jsonify({"status": "OK"}), 200

    try:
        if not request.is_json:
            return jsonify({
                "error": "Invalid request format",
                "details": "Request must be in JSON format"
            }), 400

        data = request.json
        logger.debug(f"Received outline request with data: {data}")

        # Validate and set default values
        resource_type = data.get('resourceType', 'Presentation')
        subject_focus = data.get('subjectFocus', 'General Learning')
        grade_level = data.get('gradeLevel', 'Not Specified')
        language = data.get('language', 'English')
        lesson_topic = data.get('lessonTopic', 'Exploratory Lesson')
        num_items = int(data.get('numSlides', data.get('numSections', 5)))
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
            (lesson_topic.lower().strip() == "equivalent fractions" and
             grade_level.lower().strip() == "4th grade" and
             subject_focus.lower().strip() == "math" and
             language.lower().strip() == "english")
        )
        
        if is_example:
            return jsonify(EXAMPLE_OUTLINE_DATA)

        # Validate OpenAI client
        if not client:
            return jsonify({"error": "OpenAI client not initialized"}), 500

        # Build requirements
        item_word = "slides" if resource_type.lower() == "presentation" else "sections"
        requirements = [
            f"Resource Type: {resource_type}",
            f"Grade Level: {grade_level}",
            f"Subject: {subject_focus}",
            f"Topic: {lesson_topic}",
            f"Language: {language}",
            f"Number of {item_word}: EXACTLY {num_items}",
            f"Standards: {', '.join(selected_standards) if selected_standards else 'General Learning Objectives'}"
        ]

        requirements_str = "\n".join(f"- {req}" for req in requirements)

        # Get system instructions
        system_instructions = {
            "role": "system",
            "content": get_system_prompt(resource_type)
        }

        # Create user prompt
        user_prompt = f"""
        Create a comprehensive {resource_type} with the following specifications:
        {requirements_str}

        Additional Requirements:
        {custom_prompt}
        """

        # Make the API call
        response = client.chat.completions.create(
            model="gpt-4-0125-preview",
            messages=[system_instructions, {"role": "user", "content": user_prompt}],
            max_tokens=4000,
            temperature=0.7
        )

        outline_text = response.choices[0].message.content.strip()
        logger.debug(f"Generated outline: {outline_text}")

        # Parse into clean structure
        structured_content = parse_outline_to_clean_structure(outline_text, resource_type)
        
        # Generate title
        generated_title = generate_outline_title(data, structured_content)
        logger.info(f"Generated title: {generated_title}")

        # Return clean response
        return jsonify({
            "title": generated_title,
            "messages": [outline_text],
            "structured_content": structured_content,
            "resource_type": resource_type.lower()
        })

    except Exception as e:
        logger.error(f"Error in outline generation: {str(e)}")
        logger.error(traceback.format_exc())
        
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500

# Helper route to handle CORS preflight
@outline_blueprint.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    allowed_origins = [
        'http://localhost:3000',
        'https://teacherfy.ai',
        'https://teacherfy-gma6hncme7cpghda.westus-01.azurewebsites.net'
    ]
    
    if origin in allowed_origins:
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    
    return response