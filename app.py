from flask import Flask, request, jsonify, send_file
from openai import OpenAI
from pptx import Presentation
from pptx.util import Inches
import os

# Initialize Flask app
app = Flask(__name__)

# OpenAI client configuration
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # Use your .env file for key management

@app.route("/", methods=["GET"])
def home():
    return "Welcome to Teacherfy.ai Backend!"

@app.route("/generate", methods=["POST"])
def generate_presentation():
    # Parse request data
    data = request.json
    lesson_topic = data.get("lesson_topic", "Default Topic")
    district = data.get("district", "Default District")
    
    # AI prompt creation
    prompt = f"Create 3 slide bullet points for a lesson on {lesson_topic} for {district}."
    
    try:
        # Use OpenAI API to generate content
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        slides_content = response.choices[0].message.content.strip().split("\n\n")
    except Exception as e:
        return jsonify({"error": f"Error generating AI content: {str(e)}"}), 500

    # Load PowerPoint template
    try:
        presentation = Presentation("templates/base_template.pptx")
    except Exception as e:
        return jsonify({"error": f"Error loading PowerPoint template: {str(e)}"}), 500

    # Generate slides
    for slide_content in slides_content:
        slide = presentation.slides.add_slide(presentation.slide_layouts[1])  # Adjust layout index if necessary
        title, *bullets = slide_content.split("\n")

        # Add title
        if slide.shapes.title:
            slide.shapes.title.text = title.strip()

        # Add bullet points
        content_placeholder = None
        for shape in slide.placeholders:
            if shape.placeholder_format.idx == 1:  # Content placeholder index
                content_placeholder = shape
                break

        if content_placeholder:
            content_placeholder.text = "\n".join([bullet.strip() for bullet in bullets])
        else:
            # Add a text box for content if no placeholder found
            left = Inches(1)
            top = Inches(2)
            width = Inches(8)
            height = Inches(4)
            textbox = slide.shapes.add_textbox(left, top, width, height)
            text_frame = textbox.text_frame
            for bullet in bullets:
                paragraph = text_frame.add_paragraph()
                paragraph.text = bullet.strip()

    # Save the PowerPoint file
    output_file = f"{lesson_topic}_lesson.pptx"
    try:
        presentation.save(output_file)
    except Exception as e:
        return jsonify({"error": f"Error saving PowerPoint file: {str(e)}"}), 500

    return send_file(output_file, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
