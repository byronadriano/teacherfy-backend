import os
import logging
from flask import Flask, request, jsonify, send_file
from openai import OpenAI
from pptx import Presentation
from pptx.util import Inches
import tempfile
import traceback

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def get_env_var(var_name, default=None):
    value = os.environ.get(var_name, default)
    logger.debug(f"Checking environment variable {var_name}: {value is not None}")
    if value is None:
        logger.error(f"Environment variable {var_name} not set")
        raise ValueError(f"Required environment variable {var_name} not set")
    return value

# Initialize OpenAI client with logging
try:
    client = OpenAI(
        api_key=get_env_var("OPENAI_API_KEY")
    )
except ValueError as e:
    logger.error(f"OpenAI client initialization error: {e}")
    client = None

@app.route("/", methods=["GET"])
def home():
    return "Welcome to Teacherfy.ai Backend!"

@app.route("/generate", methods=["POST"])
def generate_presentation():
    # Log incoming request details
    logger.debug(f"Received generate request: {request.json}")
    
    # Validate OpenAI client
    if client is None:
        logger.error("OpenAI client not initialized")
        return jsonify({"error": "OpenAI client not initialized"}), 500

    # Parse request data
    data = request.json
    lesson_topic = data.get("lesson_topic", "Default Topic")
    district = data.get("district", "Default District")

    # Create prompt
    prompt = f"Create 3 slide bullet points for a lesson on {lesson_topic} for {district}."

    try:
        # Generate content with OpenAI
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        slides_content = response.choices[0].message.content.strip().split("\n\n")
        logger.debug(f"Generated slides content: {slides_content}")
    except Exception as e:
        logger.error(f"Error generating AI content: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Error generating AI content: {str(e)}"}), 500

    # Verify template file existence
    template_path = "templates/base_template.pptx"
    logger.debug(f"Checking template path: {template_path}")
    logger.debug(f"Current working directory: {os.getcwd()}")
    logger.debug(f"Template file exists: {os.path.exists(template_path)}")

    try:
        # Use a temporary file for the presentation
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pptx') as temp_file:
            temp_filename = temp_file.name

        # Load PowerPoint template with additional logging
        try:
            presentation = Presentation(template_path)
        except Exception as template_error:
            logger.error(f"Error loading PowerPoint template: {template_error}")
            logger.error(traceback.format_exc())
            return jsonify({"error": f"Error loading PowerPoint template: {str(template_error)}"}), 500

        # Create slides (rest of the code remains the same as in previous version)
        for slide_content in slides_content:
            slide = presentation.slides.add_slide(presentation.slide_layouts[1])
            parts = slide_content.split("\n")
            title = parts[0].strip() if parts else "Untitled Slide"
            bullets = parts[1:] if len(parts) > 1 else []

            # Add title
            if slide.shapes.title:
                slide.shapes.title.text = title

            # Find the content placeholder
            content_placeholder = None
            for shape in slide.placeholders:
                if shape.placeholder_format.idx == 1:
                    content_placeholder = shape
                    break

            # Add bullet points
            if content_placeholder:
                content_placeholder.text = "\n".join([bullet.strip() for bullet in bullets])
            else:
                # If no placeholder, add a new text box
                left = Inches(1)
                top = Inches(2)
                width = Inches(8)
                height = Inches(4)
                textbox = slide.shapes.add_textbox(left, top, width, height)
                text_frame = textbox.text_frame
                for bullet in bullets:
                    paragraph = text_frame.add_paragraph()
                    paragraph.text = bullet.strip()

        # Save the presentation to the temporary file
        presentation.save(temp_filename)
        logger.debug(f"Presentation saved to: {temp_filename}")

        # Send the file
        return send_file(temp_filename, 
                         mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation', 
                         as_attachment=True, 
                         download_name=f"{lesson_topic}_lesson.pptx")

    except Exception as e:
        logger.error(f"Error processing PowerPoint: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Error processing PowerPoint: {str(e)}"}), 500
    finally:
        # Clean up temporary file if it exists
        if 'temp_filename' in locals() and os.path.exists(temp_filename):
            os.unlink(temp_filename)

if __name__ == "__main__":
    app.run(debug=True)