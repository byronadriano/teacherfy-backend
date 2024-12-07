import os
import logging
from flask import Flask, request, jsonify, send_file
from openai import OpenAI
from pptx import Presentation
from pptx.util import Inches
import tempfile
import traceback
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # For testing, allow all. Once works, narrow to your domain.

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_env_var(var_name, default=None):
    value = os.environ.get(var_name, default)
    logger.debug(f"Checking environment variable {var_name}: {value is not None}")
    if value is None:
        logger.error(f"Environment variable {var_name} not set")
        raise ValueError(f"Required environment variable {var_name} not set")
    return value

try:
    client = OpenAI(api_key=get_env_var("OPENAI_API_KEY"))
except ValueError as e:
    logger.error(f"OpenAI client initialization error: {e}")
    client = None

@app.route("/", methods=["GET"])
def home():
    return "Welcome to Teacherfy.ai Backend!"

@app.route("/outline", methods=["POST", "OPTIONS"])
def get_outline():
    if request.method == "OPTIONS":
        return jsonify({"status": "OK"}), 200

    if client is None:
        return jsonify({"error": "OpenAI client not initialized"}), 500

    data = request.json
    grade_level = data.get("grade_level", "Not Specified")
    subject_focus = data.get("subject_focus", "General")
    custom_prompt = data.get("custom_prompt", "")
    num_slides = min(max(data.get("num_slides", 3), 1), 10)

    prompt = f"Create a {num_slides}-slide lesson outline for a {grade_level} {subject_focus} lesson. {custom_prompt}"

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[{"role": "user", "content": prompt}]
        )
        outline_text = response.choices[0].message.content.strip()
        return jsonify({"messages": [outline_text]})
    except Exception as e:
        logging.error(f"Error getting outline: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/generate", methods=["POST", "OPTIONS"])
def generate_presentation():
    if request.method == "OPTIONS":
        return jsonify({"status": "OK"}), 200

    logger.debug(f"Received generate request: {request.json}")

    data = request.json
    lesson_topic = data.get("lesson_topic", "Default Topic")
    district = data.get("district", "Default District")
    grade_level = data.get("grade_level", "Not Specified")
    subject_focus = data.get("subject_focus", "General")
    custom_prompt = data.get("custom_prompt", "")
    num_slides = min(max(data.get("num_slides", 3), 1), 10)
    final_outline = data.get("lesson_outline", "")

    if not final_outline.strip():
        return jsonify({"error": "No outline provided"}), 400

    slides_content = final_outline.strip().split("\n\n")
    logger.debug(f"Using provided outline for slides content: {slides_content}")

    template_path = "templates/base_template.pptx"
    logger.debug(f"Template file exists: {os.path.exists(template_path)}")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pptx') as temp_file:
            temp_filename = temp_file.name

        presentation = Presentation(template_path)

        slide_start = 0
        if slides_content and "Here’s an outline" in slides_content[0]:
            slide_start = 1

        for slide_content in slides_content[slide_start:][:num_slides]:
            if not slide_content.strip():
                continue
            slide = presentation.slides.add_slide(presentation.slide_layouts[1])
            parts = slide_content.split("\n")
            title = parts[0].strip() if parts else "Untitled Slide"
            bullets = parts[1:] if len(parts) > 1 else []

            if slide.shapes.title:
                slide.shapes.title.text = title

            content_placeholder = None
            for shape in slide.placeholders:
                if shape.placeholder_format.idx == 1:
                    content_placeholder = shape
                    break

            if content_placeholder:
                content_placeholder.text = "\n".join([b.strip() for b in bullets])
            else:
                left = Inches(1)
                top = Inches(2)
                width = Inches(8)
                height = Inches(4)
                textbox = slide.shapes.add_textbox(left, top, width, height)
                text_frame = textbox.text_frame
                for bullet in bullets:
                    paragraph = text_frame.add_paragraph()
                    paragraph.text = bullet.strip()

        presentation.save(temp_filename)
        logger.debug(f"Presentation saved to: {temp_filename}")

        return send_file(temp_filename,
                         mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation',
                         as_attachment=True,
                         download_name=f"{lesson_topic}_lesson.pptx")

    except Exception as e:
        logger.error(f"Error processing PowerPoint: {e}")
        return jsonify({"error": f"Error processing PowerPoint: {str(e)}"}), 500
    finally:
        if 'temp_filename' in locals() and os.path.exists(temp_filename):
            os.unlink(temp_filename)

if __name__ == "__main__":
    app.run(debug=True)
