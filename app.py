import os
import logging
from flask import Flask, request, jsonify, send_file
from openai import OpenAI
import tempfile
from flask_cors import CORS
from presentation_generator import generate_presentation

app = Flask(__name__)
CORS(app)

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
    language = data.get("language", "")  # Add this line
    custom_prompt = data.get("custom_prompt", "")
    num_slides = min(max(data.get("num_slides", 3), 1), 10)

    prompt = f"""Create a detailed {num_slides}-slide lesson outline in {language} for a {grade_level} {subject_focus} lesson on {lesson_topic} for {district}. 

Please structure each slide with:
1. Title: Clear, descriptive title in {language}
2. Content: Main teaching points in {language}.
3. Teacher Notes: Instructions or tips (prefixed with 'TEACHER NOTE:')
4. Visual Elements: Any diagrams/images needed (prefixed with 'VISUAL:')

Format each slide as:

Slide X: [Title]
Content:
- [Main points]

Teacher Notes:
- [Teaching tips/instructions]

Visual Elements:
- [Description of visuals needed]

Additional requirements:
{custom_prompt}

Important language considerations:
- Ensure all content is in {language}
- Use age-appropriate language for {grade_level} students
- If using technical terms, provide clear explanations
- Consider including key vocabulary terms with explanations if needed

Note: Use two-column layouts for comparisons or parallel concepts."""

    try:
        response = client.chat.completions.create(
            model="gpt-4-0125-preview",
            messages=[{"role": "user", "content": prompt}]
        )
        outline_text = response.choices[0].message.content.strip()
        
        # Parse the outline into structured content
        from slide_processor import parse_outline_to_structured_content
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
            
        presentation_path = generate_presentation(outline_text, structured_content)  # Update this line
        return send_file(presentation_path, 
                        as_attachment=True,
                        download_name="lesson_presentation.pptx",
                        mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation')
        
    except Exception as e:
        logging.error(f"Error generating presentation: {e}")
        return jsonify({"error": str(e)}), 500
if __name__ == "__main__":
    app.run(debug=True)