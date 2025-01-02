import os
import logging
from flask import Flask, request, jsonify, send_file
from openai import OpenAI
from pptx import Presentation
from pptx.util import Inches
import tempfile
import traceback
from flask_cors import CORS
from presentation_generator import generate_presentation


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
    lesson_topic = data.get("lesson_topic", "")
    district = data.get("district", "")
    custom_prompt = data.get("custom_prompt", "")
    num_slides = min(max(data.get("num_slides", 3), 1), 10)

    prompt = f"Create a {num_slides}-slide lesson outline for a {grade_level} {subject_focus} lesson on {lesson_topic} for {district}. {custom_prompt}"

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
def generate_presentation_endpoint():
    if request.method == "OPTIONS":
        return jsonify({"status": "OK"}), 200

    if client is None:
        return jsonify({"error": "OpenAI client not initialized"}), 500

    try:
        data = request.json
        outline_text = data.get('lesson_outline', '')
        
        if not outline_text:
            return jsonify({"error": "No outline provided"}), 400
            
        presentation_path = generate_presentation(outline_text)
        return send_file(presentation_path, as_attachment=True, download_name="lesson_presentation.pptx")
        
    except Exception as e:
        logging.error(f"Error generating presentation: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
