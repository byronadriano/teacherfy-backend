# src/outline_routes.py - Updated with DeepSeek API support and Agent integration
import os
import re
from flask import Blueprint, request, jsonify
from src.config import logger, client
from src.utils.decorators import check_usage_limits
import json
import traceback

# Import agent coordinator for enhanced content generation
from src.agents import AgentCoordinator

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

def is_example_request(data):
    """Check if this is an example request that shouldn't count against limits."""
    return (
        data.get("use_example") or
        (data.get("lessonTopic", "").lower().strip() == "equivalent fractions" and
         data.get("gradeLevel", "").lower().strip() == "4th grade" and
         data.get("subjectFocus", "").lower().strip() == "math" and
         data.get("language", "").lower().strip() == "english")
    )

# Test data that doesn't call DeepSeek API
TEST_OUTLINE_DATA = {
    "title": "Test Lesson Plan",
    "messages": [
        """Slide 1: Test Topic Introduction
Content:
- This is a test slide for limit testing
- No DeepSeek API calls were made
- This tests the usage limits system

Slide 2: Test Content
Content:
- More test content here
- Testing monthly limits functionality
- Verifying database tracking"""
    ],
    "structured_content": [
        {
            "title": "Test Topic Introduction",
            "layout": "TITLE_AND_CONTENT",
            "content": [
                "This is a test slide for limit testing",
                "No DeepSeek API calls were made",
                "This tests the usage limits system"
            ]
        },
        {
            "title": "Test Content",
            "layout": "TITLE_AND_CONTENT",
            "content": [
                "More test content here",
                "Testing monthly limits functionality", 
                "Verifying database tracking"
            ]
        }
    ]
}

def should_use_agents(request_data):
    """Check if we should use the agent-based system for content generation"""
    # Check for explicit opt-out
    if request_data.get("use_agents") is False:
        return False  # Explicitly disabled
    
    # Check for test requests that shouldn't use agents
    if is_test_request(request_data):
        return False  # Use original test data
    
    # Default to using agents for all requests (including example bypass)
    return True

def is_test_request(request_data):
    """Check if this is a test request for limits testing."""
    return (
        request_data.get("test_limits") or
        request_data.get("lessonTopic", "").lower().startswith("test topic") or
        request_data.get("customPrompt", "").lower().find("test request for limit testing") != -1
    )

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
    
    if normalized_type == "WORKSHEET":
        return """
        YOU ARE A MASTER WORKSHEET CREATOR. Your task is to create educational worksheets with clean separation between student content and teacher guidance.

        CRITICAL MULTILINGUAL REQUIREMENTS:
        1. Write all STUDENT QUESTIONS in the target language specified by the user
        2. ALWAYS use ENGLISH keywords for parsing: "Answer:", "Differentiation tip:", "Teacher note:"
        3. NEVER translate these parsing keywords - they must remain in English regardless of content language
        4. Structure and formatting keywords must be in English for proper processing

        FOLLOW THIS EXACT FORMAT FOR EACH SECTION:

        Section X: [Clear, Descriptive Title in target language]
        Content:
        - [Question 1 in target language] (Answer: [Correct Answer in target language])
        - [Question 2 in target language] (Answer: [Correct Answer in target language])
        - [Question 3 in target language] (Answer: [Correct Answer in target language])
        - Differentiation tip: [Strategy in target language]
        - Teacher note: [Implementation guidance in target language]

        CRITICAL FORMATTING REQUIREMENTS:
        1. ALWAYS start each section with "Section X:" where X is the section number
        2. ALWAYS include the exact section header: "Content:"
        3. ALWAYS use bullet points with a hyphen (-) for all list items
        4. DO NOT use any markdown formatting (no **, __, ~~, #, etc.)
        5. DO NOT use asterisks, underscores, or other special formatting characters
        6. Use plain text only - formatting will be handled by the document processor
        7. ALWAYS put answers in parentheses with ENGLISH keyword: (Answer: [correct answer])
        8. ALWAYS use ENGLISH parsing keywords: "Differentiation tip:" and "Teacher note:"
        9. Make questions clear and specific in the target language
        10. Provide complete, accurate answers in the target language
        11. Include varied question types (calculation, short answer, multiple choice, etc.)
        QUESTION GUIDELINES:
        - Create questions that match the grade level and subject
        - Include a mix of question types: calculations, fill-in-the-blank, short answer
        - Make questions progressive in difficulty within each section
        - Ensure each question has ONE clear, correct answer
        - Word problems should be relatable and age-appropriate

        TEACHER GUIDANCE GUIDELINES:
        - Differentiation tips should be specific and actionable
        - Teacher notes should include implementation tips, common mistakes to watch for
        - Suggest materials or manipulatives when helpful
        - Provide timing estimates when relevant
        
        MULTILINGUAL EXAMPLE:
        If creating content in Spanish:
        
        Section 1: Práctica de Suma Básica
        Content:
        - Resuelve: 25 + 17 = ____ (Answer: 42)
        - ¿Cuál es la suma de 34 y 28? (Answer: 62)
        - Completa: 45 + ___ = 73 (Answer: 28)
        - María tiene 15 pegatinas y compra 23 más. ¿Cuántas pegatinas tiene ahora? (Answer: 38)
        - Differentiation tip: Proporciona líneas numéricas o bloques base diez para estudiantes visuales
        - Teacher note: Recuerda a los estudiantes alinear los números por valor posicional
        
        IMPORTANT: Notice that questions and explanations are in Spanish, but "Answer:", "Differentiation tip:", and "Teacher note:" remain in English for proper parsing.
        """
    
    elif normalized_type == "QUIZ":
        return """
        YOU ARE A MASTER QUIZ AND TEST CREATOR. Your task is to produce educational assessments with clean, professional formatting.

        CRITICAL MULTILINGUAL REQUIREMENTS:
        1. Write all STUDENT QUESTIONS in the target language specified by the user
        2. ALWAYS use ENGLISH keywords for parsing: "Answer:", "Differentiation tip:", "Teacher note:"
        3. NEVER translate these parsing keywords - they must remain in English regardless of content language
        4. Structure and formatting keywords must be in English for proper processing

        FOLLOW THIS EXACT FORMAT FOR EACH SECTION:

        Section X: [Clear, Descriptive Title in target language]
        Content:
        - [Question 1 in target language with complete wording] (Answer: [Correct Answer])
        - [Question 2 in target language with complete wording] (Answer: [Correct Answer])
        - [Additional questions with answers as needed]

        - Differentiation tip: [Strategy in target language]
        - Teacher note: [Instructions in target language]

        CRITICAL FORMATTING REQUIREMENTS:
        1. ALWAYS start each section with "Section X:" where X is the section number
        2. ALWAYS include the exact section header: "Content:"
        3. ALWAYS use bullet points with a hyphen (-) for all list items
        4. DO NOT use any markdown formatting (no **, __, ~~, #, etc.)
        5. DO NOT use asterisks, underscores, or other special formatting characters
        6. Use plain text only - formatting will be handled by the document processor
        7. Use A) B) C) D) for multiple choice items in target language
        8. Make each question self-contained and clear in target language
        9. ALWAYS use ENGLISH parsing keywords: (Answer: [answer]), "Differentiation tip:", "Teacher note:"
        10. Content can be in any language, but parsing keywords must be English

        EXAMPLE OF CORRECT FORMAT:
        Section 1: Understanding Fractions
        Content:
        - What fraction represents half of a pizza? A) 1/4 B) 1/2 C) 3/4 D) 1/3 (Answer: B)
        - Write the fraction that shows 3 out of 8 equal parts. (Answer: 3/8)

        - Differentiation tip: Allow students to sketch visuals or use manipulatives
        - Teacher note: Review numerator/denominator before the quiz if needed
        """
    
    elif normalized_type == "LESSON_PLAN":
        return """
        YOU ARE A MASTER LESSON PLAN CREATOR. Your task is to produce comprehensive, ready-to-use lesson plans.

        CRITICAL MULTILINGUAL REQUIREMENTS:
        1. Write all CONTENT in the target language specified by the user
        2. ALWAYS use ENGLISH keywords for parsing: "Teacher action:", "Differentiation tip:", "Assessment check:"
        3. NEVER translate these parsing keywords - they must remain in English regardless of content language

        FOLLOW THIS EXACT FORMAT FOR EACH SECTION:

        Section X: [Clear, Descriptive Title in target language]
        Content:
        - [Core learning content in target language]
        - [Examples, definitions, or guided steps in target language]
        - [Follow-up discussion or practice prompt in target language]

        - Teacher action: [Direct instruction in target language]
        - Teacher action: [Another instructional step in target language]
        - Teacher action: [Classroom management strategy in target language]

        - Differentiation tip: [Modify for different students in target language]
        - Assessment check: [Quick way to monitor understanding in target language]

        CRITICAL FORMATTING REQUIREMENTS:
        1. ALWAYS start each section with "Section X:" where X is the section number
        2. ALWAYS include the exact section header: "Content:"
        3. ALWAYS use bullet points with a hyphen (-) for all list items
        4. DO NOT use any markdown formatting (no **, __, ~~, #, etc.)
        5. ALWAYS use ENGLISH parsing keywords: "Teacher action:", "Differentiation tip:", "Assessment check:"
        6. Content can be in target language, but parsing keywords must be English
        EXAMPLE OF CORRECT FORMAT:
        Section 1: Lesson Introduction and Objectives
        Content:
        - Students will understand the concept of equivalent fractions
        - Show examples: 1/2 = 2/4, 3/6 = 1/2
        - Ask: Can you think of two ways to show 1/2?

        - Teacher action: Use visual models to show two fractions of the same value
        - Teacher action: Call on students to describe fraction bars aloud
        - Teacher action: Reinforce vocabulary using a visual anchor chart

        - Differentiation tip: Use fraction tiles for hands-on exploration
        - Assessment check: Have students hold up a card showing whether two fractions are equal
        """
    
    else:
        # Default to presentation format
        return """
        YOU ARE A MASTER CLASSROOM PRESENTATION CREATOR. Your task is to create slide content with clean, professional formatting.

        CRITICAL MULTILINGUAL REQUIREMENTS:
        1. Write all SLIDE CONTENT in the target language specified by the user
        2. Keep structure keywords in English: "Slide X:", "Content:"
        3. This ensures proper parsing regardless of content language

        FOLLOW THIS EXACT FORMAT FOR EACH SLIDE:

        Slide X: [Engaging and Descriptive Slide Title in target language]
        Content:
        - [Actual content for students in target language]
        - [Clear explanation or concept in target language]
        - [Example or application in target language]
        - [Question for students in target language]
        - [Summary or connection in target language]

        CRITICAL FORMATTING REQUIREMENTS:
        1. ALWAYS start each slide with "Slide X:" where X is the slide number
        2. ALWAYS include the "Content:" section header in English
        3. ALWAYS use bullet points with a hyphen (-) for all list items
        4. DO NOT use any markdown formatting (no **, __, ~~, #, etc.)
        5. Write slide content in the target language, but keep structure in English
        6. EXACTLY match the requested number of slides
        7. Write DIRECT TEACHING CONTENT, NOT meta-instructions
        8. First slide should introduce specific learning objectives tied to lesson content
        9. Last slide should include key takeaways or review points
        10. Write as if speaking directly to students
        
        EXAMPLE OF CORRECT FORMAT:
        
        Slide 1: Understanding Fractions
        Content:
        - A fraction represents a part of a whole
        - The numerator (top number) tells us how many parts we have
        - The denominator (bottom number) tells us the total number of equal parts
        - Fractions help us measure ingredients in cooking and divide objects equally
        - Students will identify, compare, and solve problems using fractions
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
@check_usage_limits(action_type='generation')  # This will check and increment generation limits
def get_outline():
    """Generate a lesson outline using DeepSeek API - UNIFIED ENDPOINT"""
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

        # Check for example outline first (before any processing)
        if is_example_request(data):
            # Check if this should use agents for enhanced example content
            if should_use_agents(data):
                logger.info("Example request - using agents for enhanced generation")
                # Continue to agent processing below
            else:
                logger.info("Example request - returning standard example outline")
                return jsonify(EXAMPLE_OUTLINE_DATA)

        # NEW: Check for test request (counts against limits but doesn't call DeepSeek)
        if is_test_request(data):
            logger.info("Returning test outline - usage incremented but no DeepSeek call")
            # Generate a unique title for the test
            test_title = f"Test Lesson - {data.get('lessonTopic', 'Generic Test')}"
            test_data = TEST_OUTLINE_DATA.copy()
            test_data["title"] = test_title
            return jsonify(test_data)

        # Validate and set default values for real DeepSeek requests
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

        # Validate DeepSeek client
        if not client:
            return jsonify({"error": "DeepSeek client not initialized"}), 500

        # NEW: Check if we should use the agent-based system
        if should_use_agents(data):
            logger.info("Using AGENT-BASED system for enhanced content generation")
            
            try:
                # Initialize agent coordinator
                agent_coordinator = AgentCoordinator()
                
                # Extract requested resources info if available from session/context
                # For now, we'll use the current resource type but plan for multi-resource support
                requested_resources = [resource_type]  # Future: extract from frontend session
                
                # Generate content using agents
                structured_content = agent_coordinator.generate_structured_content(
                    lesson_topic=lesson_topic,
                    subject_focus=subject_focus,
                    grade_level=grade_level,
                    resource_type=resource_type,
                    language=language,
                    num_sections=num_items,
                    standards=selected_standards,
                    custom_requirements=custom_prompt,
                    requested_resources=requested_resources
                )
                
                # Generate title using existing function
                generated_title = generate_outline_title(data, structured_content)
                
                # Return clean structured format - no legacy duplication
                logger.info(f"Agent-based generation complete: {len(structured_content)} sections")
                return jsonify({
                    "title": generated_title,
                    "structured_content": structured_content,
                    "resource_type": resource_type.lower(),
                    "generation_method": "agents"
                })
                
            except Exception as e:
                logger.error(f"Agent-based generation failed: {e}")
                logger.info("Falling back to original DeepSeek system")
                # Continue to original system below

        logger.info("Using ORIGINAL DeepSeek system for content generation")

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

        # Make the DeepSeek API call using the deepseek-chat model
        response = client.chat.completions.create(
            model="deepseek-chat",  # Using DeepSeek's chat model
            messages=[system_instructions, {"role": "user", "content": user_prompt}],
            max_tokens=4000,
            temperature=0.7,
            stream=False
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