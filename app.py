import os
import json
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

# Load example outlines
EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), 'examples')
EXAMPLE_OUTLINES = {}

EXAMPLE_OUTLINE_DATA = {
  "messages": [
    "Slide 1: Let's Explore Equivalent Fractions!\nContent:\n- Students will be able to recognize and create equivalent fractions in everyday situations, like sharing cookies, pizza, or our favorite Colorado trail mix.\n- Students will be able to explain why different fractions can show the same amount using pictures and numbers.\n\nTeacher Notes:\n- Begin with students sharing their experiences with fractions in their daily lives\n- Use culturally relevant examples from Denver communities\n\nVisual Elements:\n- Interactive display showing local treats divided into equivalent parts\n- Student-friendly vocabulary cards with pictures"
  ],
  "structured_content": [
    {
      "title": "Let's Explore Equivalent Fractions!",
      "layout": "TITLE_AND_CONTENT",
      "content": [
        "Today we're going on a fraction adventure!",
        "- Students will be able to recognize and create equivalent fractions in everyday situations, like sharing cookies, pizza, or our favorite Colorado trail mix",
        "- Students will be able to explain why different fractions can show the same amount using pictures and numbers",
        "- Let's start by thinking about times when we share things equally!"
      ],
      "teacher_notes": [
        "Begin with students sharing their experiences with fractions in their daily lives",
        "Use culturally relevant examples from Denver communities",
        "Encourage bilingual students to share fraction terms in their home language"
      ],
      "visual_elements": [
        "Interactive display showing local treats divided into equivalent parts",
        "Student-friendly vocabulary cards with pictures"
      ],
      "left_column": [],
      "right_column": []
    },
    {
      "title": "What Are Equivalent Fractions?",
      "layout": "TITLE_AND_CONTENT",
      "content": [
        "Let's learn our fraction vocabulary!",
        "- Imagine sharing a breakfast burrito with your friend - you can cut it in half (1/2) or into four equal pieces and take two (2/4). You get the same amount!",
        "- The top number (numerator) tells us how many pieces we have",
        "- The bottom number (denominator) tells us how many total equal pieces",
        "- When fractions show the same amount, we call them equivalent"
      ],
      "teacher_notes": [
        "Use local food examples familiar to Denver students",
        "Connect math vocabulary to real experiences",
        "Encourage students to create their own examples"
      ],
      "visual_elements": [
        "Animation of a burrito being cut into different equivalent portions",
        "Interactive fraction wall labeled in English and Spanish",
        "Hands-on fraction strips for each student"
      ],
      "left_column": [],
      "right_column": []
    },
    {
      "title": "Finding Equivalent Fractions Together",
      "layout": "TWO_COLUMNS",
      "content": [],
      "teacher_notes": [
        "Use Rocky Mountain National Park trail maps for real-world connections",
        "Encourage peer discussion in preferred language",
        "Model think-aloud strategy"
      ],
      "visual_elements": [
        "Trail map showing different fraction representations",
        "Digital manipulatives for student exploration"
      ],
      "left_column": [
        "Let's practice together!",
        "- When we multiply 1/2 by 2/2, we get 2/4",
        "- It's like taking a hiking trail that's 1/2 mile long and marking it every quarter mile - you'll have 2/4 of the trail at the same spot as 1/2!",
        "- Your turn: Try finding an equivalent fraction for 2/3"
      ],
      "right_column": [
        "Check your understanding:",
        "- Use your fraction strips to show how 1/2 = 2/4",
        "- Draw a picture to prove your answer",
        "- Share your strategy with your partner"
      ]
    },
    {
      "title": "Your Turn to Create!",
      "layout": "TITLE_AND_CONTENT",
      "content": [
        "Time to become fraction experts!",
        "- Work with your partner to create equivalent fraction cards",
        "- Use different colors to show equal parts",
        "- Challenge: Can you find three different fractions that equal 1/2?",
        "- Bonus: Create a story problem using equivalent fractions and your favorite Denver activity"
      ],
      "teacher_notes": [
        "Provide bilingual instruction cards",
        "Allow student choice in examples",
        "Support native language use in discussions"
      ],
      "visual_elements": [
        "Sample fraction cards with local themes",
        "Student workspace organization guide",
        "Visual success criteria"
      ],
      "left_column": [],
      "right_column": []
    },
    {
      "title": "Show What You Know!",
      "layout": "TITLE_AND_CONTENT",
      "content": [
        "Let's celebrate what we learned!",
        "- Create three equivalent fractions for 3/4",
        "- Draw a picture showing how you know they're equal",
        "- Write a story about using equivalent fractions in your neighborhood",
        "- Share your favorite way to remember equivalent fractions"
      ],
      "teacher_notes": [
        "Provide multiple ways to demonstrate understanding",
        "Accept explanations in English or home language",
        "Use exit ticket responses to plan next lesson"
      ],
      "visual_elements": [
        "Culturally responsive exit ticket template",
        "Digital portfolio upload guide",
        "Self-assessment checklist in multiple languages"
      ],
      "left_column": [],
      "right_column": []
    }
  ]
};

def load_example_outlines():
    """Load all example outline JSON files from the examples directory"""
    try:
        # Create examples directory if it doesn't exist
        if not os.path.exists(EXAMPLES_DIR):
            os.makedirs(EXAMPLES_DIR)
        
        # Ensure example file exists
        example_path = os.path.join(EXAMPLES_DIR, 'equivalent_fractions_outline.json')
        if not os.path.exists(example_path):
            with open(example_path, 'w', encoding='utf-8') as f:
                json.dump(EXAMPLE_OUTLINE_DATA, f, indent=2)  # We'll define this constant
        
        # Load all examples
        for filename in os.listdir(EXAMPLES_DIR):
            if filename.endswith('.json'):
                with open(os.path.join(EXAMPLES_DIR, filename), 'r', encoding='utf-8') as f:
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

@app.route("/outline", methods=["POST", "OPTIONS"])
def get_outline():
    if request.method == "OPTIONS":
        return jsonify({"status": "OK"}), 200

    data = request.json
    logger.debug(f"Received outline request with data: {data}")
    
    # Check for example case
    is_example = (
        data.get("use_example") or
        (data.get("lesson_topic", "").lower().strip() == "equivalent fractions" and
         data.get("grade_level", "").lower().strip() == "4th grade" and
         data.get("subject_focus", "").lower().strip() == "math")
    )
    
    logger.debug(f"Is example request: {is_example}")

    if is_example:
        example_data = EXAMPLE_OUTLINES.get("equivalent_fractions_outline")
        logger.debug(f"Found example data: {bool(example_data)}")
        if example_data:
            return jsonify(example_data)
        # If example not found, fall back to default
        return jsonify(EXAMPLE_OUTLINE_DATA)


    # Regular outline generation
    if client is None:
        return jsonify({"error": "OpenAI client not initialized"}), 500

    # Instead of creating a new prompt here, use the one from frontend
    prompt = data.get("custom_prompt")
    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    try:
        response = client.chat.completions.create(
            model="gpt-4-0125-preview",
            messages=[{"role": "user", "content": prompt}]
        )
        outline_text = response.choices[0].message.content.strip()
        
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
        logger.debug(f"Received generation request with data keys: {data.keys()}")
        
        outline_text = data.get('lesson_outline', '')
        structured_content = data.get('structured_content')        
        
        if not structured_content:
            logger.error("No structured content provided in request")
            return jsonify({"error": "No structured content provided"}), 400
            
        logger.debug(f"Generating presentation with {len(structured_content)} slides")
        presentation_path = generate_presentation(outline_text, structured_content)
        
        if not os.path.exists(presentation_path):
            logger.error(f"Generated presentation file not found at: {presentation_path}")
            return jsonify({"error": "Failed to create presentation file"}), 500
            
        logger.debug(f"Sending presentation file: {presentation_path}")
        return send_file(
            presentation_path, 
            as_attachment=True,
            download_name="lesson_presentation.pptx",
            mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation'
        )
        
    except Exception as e:
        logger.error(f"Error generating presentation: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)