# resources/routes/resources.py - Updated with image support and multi-resource generation
from flask import Blueprint, request, jsonify, send_file, session
from config.settings import logger, SCOPES
from resources.types import ResourceType, get_resource_handler
from agents.coordinator import AgentCoordinator
from google.oauth2.credentials import Credentials
import os
import traceback

resource_blueprint = Blueprint("resource_blueprint", __name__)

def _slugify_filename(text: str) -> str:
    """Create a safe, readable filename fragment from arbitrary text."""
    if not text:
        return "lesson"
    # Basic cleanup
    cleaned = ''.join(ch if ch.isalnum() or ch in (' ', '-', '_') else ' ' for ch in text)
    # Collapse whitespace and dashes, lower-case
    cleaned = ' '.join(cleaned.split()).strip().lower()
    # Replace spaces with dashes
    cleaned = cleaned.replace(' ', '-')
    # Truncate to a sensible length
    return cleaned[:80] or "lesson"

def _extract_title_for_filename(structured_content, handler_type: str) -> str:
    """Pick a good title for the output filename based on resource type.
    - presentation: prefer title from the 2nd section (index 1) if present
    - others: use title from the 1st section (index 0)
    Fallbacks to generic names if missing.
    """
    try:
        if not isinstance(structured_content, list) or not structured_content:
            return "lesson"

        index = 1 if handler_type == "presentation" and len(structured_content) > 1 else 0
        section = structured_content[index] or {}
        title = section.get('title') or section.get('section_title') or ''
        # As a fallback, try to infer from content
        if not title:
            content = section.get('content') or []
            if isinstance(content, list) and content:
                title = content[0]
        return _slugify_filename(str(title))
    except Exception:
        return "lesson"

@resource_blueprint.route("/generate/<resource_type>", methods=["POST", "OPTIONS"])
def generate_resource_endpoint(resource_type):
    """Generate a resource file based on the specified resource type with optional image support."""
    if request.method == "OPTIONS":
        return jsonify({"status": "OK"}), 200

    logger.info(f"Generate {resource_type} request received from: {request.remote_addr}")
    
    try:
        data = request.get_json()
    except Exception as e:
        logger.error(f"Error parsing JSON: {e}")
        data = request.form.to_dict()
    
    structured_content = data.get('structured_content')
    
    # Check for Google Slides output option
    output_format = data.get('output_format', 'file')  # 'file' or 'google_slides'
    
    # Default to False to avoid expensive image generation unless explicitly requested
    # Accept either snake_case (include_images) or camelCase (includeImages) from frontend
    include_images = False
    if isinstance(data, dict):
        if 'include_images' in data:
            include_images = data.get('include_images', False)
        else:
            include_images = data.get('includeImages', False)
    
    if not structured_content:
        logger.error("No structured content provided")
        return jsonify({"error": "No structured content provided"}), 400
    
    logger.info(f"Processing resource generation request for: {resource_type} with {len(structured_content)} items (images: {include_images})")
    
    try:
        # Normalize resource type - strip all non-alphanumeric chars
        normalized_resource_type = resource_type.lower().replace('-', '_').replace(' ', '_')
        
        # Log the received and normalized resource type
        logger.info(f"Resource type received: '{resource_type}', normalized to: '{normalized_resource_type}', images: {include_images}, output: {output_format}")
        
        # Better resource type normalization with improved mapping
        if "quiz" in normalized_resource_type or "test" in normalized_resource_type:
            handler_type = "quiz"
        elif "lesson" in normalized_resource_type and "plan" in normalized_resource_type:
            handler_type = "lesson_plan"
        elif "worksheet" in normalized_resource_type or "activity" in normalized_resource_type:
            handler_type = "worksheet"
        else:
            handler_type = "presentation"  # Default
        
        # Handle Google Slides output for presentations
        if handler_type == "presentation" and output_format == "google_slides":
            # Check authentication for Google Slides
            if 'credentials' not in session:
                return jsonify({
                    "error": "Authentication required for Google Slides generation",
                    "needsAuth": True
                }), 401
            
            # Get credentials from session
            credentials_data = session.get('credentials')
            if not credentials_data:
                return jsonify({
                    "needsAuth": True,
                    "error": "No Google credentials found in session"
                }), 401
            
            from google.oauth2.credentials import Credentials
            credentials = Credentials(
                token=credentials_data['token'],
                refresh_token=credentials_data.get('refresh_token'),
                token_uri=credentials_data['token_uri'],
                client_id=credentials_data['client_id'],
                client_secret=credentials_data['client_secret'],
                scopes=SCOPES
            )
            
            # Use Google Slides handler
            from resources.handlers.google_slides_handler import GoogleSlidesHandler
            handler = GoogleSlidesHandler(structured_content, credentials, include_images=include_images)
            presentation_url, presentation_id = handler.generate()
            
            logger.info(f"Successfully generated Google Slides presentation: {presentation_url}")
            
            return jsonify({
                "success": True,
                "presentation_url": presentation_url,
                "presentation_id": presentation_id,
                "message": "Google Slides presentation created successfully",
                "slide_count": len(structured_content),
                "output_format": "google_slides"
            })
        
        # Standard file generation flow
        logger.info(f"Selected handler_type: '{handler_type}' for resource_type: '{resource_type}'")
        
        # Get the appropriate handler using the resource_types module
        from resources.types import get_resource_handler
        
        # Create the handler instance with image preference
        handler = get_resource_handler(handler_type, structured_content, include_images=include_images)
        
        # Generate the resource
        file_path = handler.generate()
        
        # Log success
        logger.info(f"Successfully generated {handler_type} resource at: {file_path}")
        
        # Get appropriate file extension
        _, file_extension = os.path.splitext(file_path)
        mime_types = {
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.pdf': 'application/pdf'
        }
        
        mime_type = mime_types.get(file_extension, 'application/octet-stream')
        
        # Clean resource type for filename
        clean_resource_type = handler_type.replace('_', '-')
        
        # Build a more descriptive filename using section titles
        base_title = _extract_title_for_filename(structured_content, handler_type)
        download_name = f"{base_title}-{clean_resource_type}{file_extension}"

        return send_file(
            file_path,
            as_attachment=True,
            download_name=download_name,
            mimetype=mime_type,
            etag=False,
            conditional=False,
            last_modified=None
        )
        
    except ImportError as e:
        # Specific handling for import errors which could indicate missing handlers
        logger.error(f"ImportError while handling resource type '{resource_type}': {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": f"Resource type '{resource_type}' is not supported.",
            "details": "The requested resource handler could not be loaded."
        }), 400
    except Exception as e:
        # General error handling
        logger.error(f"Error generating {resource_type}: {e}", exc_info=True)
        return jsonify({
            "error": str(e),
            "error_type": type(e).__name__,
            "stack_trace": traceback.format_exc()
        }), 500
            
# For backward compatibility - maintain the original /generate endpoint 
# that defaults to presentation type
@resource_blueprint.route("/generate", methods=["POST", "OPTIONS"])
def generate_presentation_endpoint():
    """Generate a PowerPoint presentation (.pptx) for download with optional image support."""
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
    resource_type = data.get('resource_type', 'presentation').lower()
    structured_content = data.get('structured_content')
    
    # Check for Google Slides output option
    output_format = data.get('output_format', 'file')  # 'file' or 'google_slides'
    
    # Default to False to avoid expensive image generation unless explicitly requested
    # Accept either snake_case (include_images) or camelCase (includeImages) from frontend
    include_images = False
    if isinstance(data, dict):
        if 'include_images' in data:
            include_images = data.get('include_images', False)
        else:
            include_images = data.get('includeImages', False)
    
    if not structured_content:
        logger.error("No structured content provided")
        return jsonify({"error": "No structured content provided"}), 400
    
    
    logger.info(f"Processing generate request with {len(structured_content)} items for resource type: {resource_type} (images: {include_images}, output: {output_format})")
    
    return generate_resource_endpoint(resource_type)

@resource_blueprint.route("/generate-multiple-resources", methods=["POST", "OPTIONS"])
def generate_multiple_resources_endpoint():
    """Generate multiple aligned resources in a single optimized API call."""
    if request.method == "OPTIONS":
        return jsonify({"status": "OK"}), 200

    logger.info(f"Multi-resource generation request from: {request.remote_addr}")
    
    try:
        data = request.get_json()
    except Exception as e:
        logger.error(f"Error parsing JSON: {e}")
        return jsonify({"error": "Invalid JSON data"}), 400
    
    # Extract and validate required fields
    lesson_topic = data.get('lessonTopic')
    subject_focus = data.get('subjectFocus') 
    grade_level = data.get('gradeLevel')
    resource_types = data.get('resourceTypes', [])
    
    if not all([lesson_topic, subject_focus, grade_level]):
        logger.error("Missing required fields: lessonTopic, subjectFocus, or gradeLevel")
        return jsonify({"error": "Missing required fields: lessonTopic, subjectFocus, gradeLevel"}), 400
    
    if not resource_types or len(resource_types) == 0:
        logger.error("No resource types specified")
        return jsonify({"error": "At least one resource type must be specified"}), 400
    
    # Convert resource types to lowercase for consistency
    normalized_resource_types = [rt.lower() for rt in resource_types]
    
    logger.info(f"Generating {len(normalized_resource_types)} resources: {normalized_resource_types}")
    
    try:
        # Initialize the agent coordinator
        coordinator = AgentCoordinator()
        
        # Generate multiple aligned resources
        results = coordinator.generate_multiple_resources(
            lesson_topic=lesson_topic,
            subject_focus=subject_focus,
            grade_level=grade_level,
            language=data.get('language', 'English'),
            resource_types=normalized_resource_types,
            standards=data.get('selectedStandards', []),
            custom_requirements=data.get('custom_prompt', ''),
            num_sections=data.get('numSlides', 5)
        )
        
        logger.info(f"Successfully generated {len(results)} aligned resources")
        
        # Return structured content for frontend processing
        return jsonify({
            'success': True,
            'structured_content': results,
            'generation_method': 'optimized_multiple_resources',
            'resource_types': list(results.keys()),
            'message': f'Generated {len(results)} aligned resources successfully'
        })
        
    except Exception as e:
        logger.error(f"Error in multi-resource generation: {e}", exc_info=True)
        return jsonify({
            "error": str(e),
            "error_type": type(e).__name__,
            "message": "Failed to generate multiple resources"
        }), 500

