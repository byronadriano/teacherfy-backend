import os
import json
import logging
from flask import Flask, request, jsonify, send_file
from openai import OpenAI
import tempfile
from flask_cors import CORS
from presentation import generate_presentation
from slides import parse_outline_to_structured_content

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Update examples directory path
EXAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'examples')
EXAMPLE_OUTLINES = {}

def load_example_outlines():
    """Load all example outline JSON files from the examples directory"""
    try:
        if not os.path.isdir(EXAMPLES_DIR):
            raise FileNotFoundError(f"Examples directory not found: {EXAMPLES_DIR}")
        
        for filename in os.listdir(EXAMPLES_DIR):
            if filename.endswith('.json'):
                with open(os.path.join(EXAMPLES_DIR, filename), 'r') as f:
                    name = os.path.splitext(filename)[0]
                    EXAMPLE_OUTLINES[name] = json.load(f)
        logger.debug(f"Loaded {len(EXAMPLE_OUTLINES)} example outlines")
    except Exception as e:
        logger.error(f"Error loading example outlines: {e}")

load_example_outlines()

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
    return jsonify({"message": "Welcome to the Teacherfy.ai backend!"}), 200

@app.route("/outline", methods=["POST", "OPTIONS"])
def get_outline():
    if request.method == "OPTIONS":
        return jsonify({"status": "OK"}), 200

    data = request.json
    
    if data.get("use_example"):
        example_name = data.get("example_name", "equivalent_fractions_outline")
        if example_name in EXAMPLE_OUTLINES:
            return jsonify(EXAMPLE_OUTLINES[example_name])
        return jsonify({"error": "Example not found"}), 404

    if client is None:
        return jsonify({"error": "OpenAI client not initialized"}), 500

    prompt = data.get("custom_prompt")
    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    try:
        response = client.chat.completions.create(
            model="gpt-4-0125-preview",
            messages=[{"role": "user", "content": prompt}]
        )
        outline_text = response.choices[0].message.content.strip()
        structured_content = parse_outline_to_structured_content(outline_text)
        
        return jsonify({
            "messages": [outline_text],
            "structured_content": structured_content
        })
    except Exception as e:
        logging.error(f"Error getting outline: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/generate", methods=["POST", "OPTIONS"])
def generate_presentation_endpoint():
    if request.method == "OPTIONS":
        return jsonify({"status": "OK"}), 200

    try:
        data = request.json
        outline_text = data.get('lesson_outline', '')
        structured_content = data.get('structured_content')        
        if not outline_text:
            return jsonify({"error": "No outline provided"}), 400
            
        presentation_path = generate_presentation(outline_text, structured_content)
        return send_file(presentation_path, 
                        as_attachment=True,
                        download_name="lesson_presentation.pptx",
                        mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation')
        
    except Exception as e:
        logging.error(f"Error generating presentation: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
