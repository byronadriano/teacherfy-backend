# src/resource_routes.py
from flask import Blueprint, request, jsonify, send_file
from src.config import logger
from src.resource_types import ResourceType, get_resource_handler
# Remove the usage decorator for download endpoints
import os
import traceback

resource_blueprint = Blueprint("resource_blueprint", __name__)

@resource_blueprint.route("/generate/<resource_type>", methods=["POST", "OPTIONS"])
# No usage limit decorator - downloads are unlimited once content is generated
def generate_resource_endpoint(resource_type):
    """Generate a resource file based on the specified resource type - NO USAGE LIMITS."""
    if request.method == "OPTIONS":
        return jsonify({"status": "OK"}), 200

    logger.info(f"Generate {resource_type} request received from: {request.remote_addr}")
    
    try:
        data = request.get_json()
    except Exception as e:
        logger.error(f"Error parsing JSON: {e}")
        data = request.form.to_dict()
    
    structured_content = data.get('structured_content')
    
    if not structured_content:
        logger.error("No structured content provided")
        return jsonify({"error": "No structured content provided"}), 400
    
    logger.info(f"Processing resource generation request for: {resource_type} with {len(structured_content)} items")
    
    try:
        # Normalize resource type - strip all non-alphanumeric chars
        normalized_resource_type = resource_type.lower().replace('-', '_').replace(' ', '_')
        
        # Log the received and normalized resource type
        logger.info(f"Resource type received: '{resource_type}', normalized to: '{normalized_resource_type}'")
        
        # Better resource type normalization with improved mapping
        if "quiz" in normalized_resource_type or "test" in normalized_resource_type:
            handler_type = "quiz"
        elif "lesson" in normalized_resource_type and "plan" in normalized_resource_type:
            handler_type = "lesson_plan"
        elif "worksheet" in normalized_resource_type or "activity" in normalized_resource_type:
            handler_type = "worksheet"
        else:
            handler_type = "presentation"  # Default
        
        logger.info(f"Selected handler_type: '{handler_type}' for resource_type: '{resource_type}'")
        
        # Get the appropriate handler using the resource_types module
        from src.resource_types import get_resource_handler
        
        # Create the handler instance
        handler = get_resource_handler(handler_type, structured_content)
        
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
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"lesson_{clean_resource_type}{file_extension}",
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
# No usage limit decorator - downloads are unlimited once content is generated
def generate_presentation_endpoint():
    """Generate a PowerPoint presentation (.pptx) for download - NO USAGE LIMITS."""
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
    
    if not structured_content:
        logger.error("No structured content provided")
        return jsonify({"error": "No structured content provided"}), 400
    
    logger.info(f"Processing generate request with {len(structured_content)} items for resource type: {resource_type}")
    
    return generate_resource_endpoint(resource_type)