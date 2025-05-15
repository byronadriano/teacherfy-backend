# src/resource_routes.py
from flask import Blueprint, request, jsonify, send_file
from src.config import logger
from src.resource_types import ResourceType, get_resource_handler
from src.utils.decorators import check_usage_limits
import os
import traceback

resource_blueprint = Blueprint("resource_blueprint", __name__)

@resource_blueprint.route("/generate/<resource_type>", methods=["POST", "OPTIONS"])
@check_usage_limits(action_type='download')
def generate_resource_endpoint(resource_type):
    """Generate a resource file based on the specified resource type."""
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
    
    logger.info(f"Processing generate {resource_type} request with {len(structured_content)} slides/sections")
    
    try:
        # Normalize resource type
        normalized_type = resource_type.lower().replace(" ", "_").replace("/", "_")
        if normalized_type in ['quiz', 'test', 'quiz_test']:
            normalized_type = 'quiz'
        elif normalized_type in ['worksheet', 'activity']:
            normalized_type = 'worksheet'
        elif normalized_type in ['lesson_plan', 'lesson']:
            normalized_type = 'lesson_plan'
        else:
            normalized_type = 'presentation'
            
        logger.info(f"Normalized resource type: {normalized_type}")
        
        # Get the appropriate handler
        handler = get_resource_handler(normalized_type, structured_content)
        
        # Generate the resource
        file_path = handler.generate()
        
        # Get file extension for proper MIME type
        _, file_extension = os.path.splitext(file_path)
        mime_types = {
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.pdf': 'application/pdf'
        }
        
        mime_type = mime_types.get(file_extension, 'application/octet-stream')
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"lesson_{normalized_type}{file_extension}",
            mimetype=mime_type,
            etag=False,
            conditional=False,
            last_modified=None
        )
        
    except Exception as e:
        logger.error(f"Error generating {resource_type}: {e}", exc_info=True)
        return jsonify({
            "error": str(e),
            "error_type": type(e).__name__,
            "stack_trace": traceback.format_exc()
        }), 500
        
# For backward compatibility - maintain the original /generate endpoint 
# that defaults to presentation type
@resource_blueprint.route("/generate", methods=["POST", "OPTIONS"])
@check_usage_limits(action_type='download')
def generate_presentation_endpoint():
    """Generate a PowerPoint presentation (.pptx) for download."""
    # Just delegate to the new endpoint with presentation type
    return generate_resource_endpoint("presentation")