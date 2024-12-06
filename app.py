from flask import Flask, request, jsonify, send_file
import openai
from pptx import Presentation
from pptx.util import Inches
import os

app = Flask(__name__)

# Set the OpenAI API key from environment variables
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route("/", methods=["GET"])
def home():
    return "Welcome to Teacherfy.ai Backend!"

@app.route("/generate", methods=["POST"])
def generate_presentation():
    # Parse request data
    data = request.json
    lesson_topic = data.get("lesson_topic", "Default Topic")
    district = data.get("district", "Default District")

    # Create prompt for OpenAI
    prompt = f"Create 3 slide bullet points for a lesson on {lesson_topic} for {district}."

    # Generate slides content using OpenAI
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",  # Replace with the correct model you have access to (e.g., "gpt-4", "gpt-3.5-turbo")
            messages=[{"role": "user", "content": prompt}],
        )
        slides_content = response.choices[0].message.content.strip().split("\n\n")
    except Exception as e:
        return jsonify({"error": f"Error generating AI content: {str(e)}"}), 500

    # Load the PowerPoint template
    try:
        presentation = Presentation("templates/base_template.pptx")
    except Exception as e:
        return jsonify({"error": f"Error loading PowerPoint template: {str(e)}"}), 500

    # Create slides based on the AI-generated content
    for slide_content in slides_content:
        slide = presentation.slides.add_slide(presentation.slide_layouts[1])  # Adjust layout if necessary
        parts = slide_content.split("\n")
        title = parts[0].strip() if parts else "Untitled Slide"
        bullets = parts[1:] if len(parts) > 1 else []

        # Add title to the slide (if placeholder exists)
        if slide.shapes.title:
            slide.shapes.title.text = title

        # Find the content placeholder for bullets
        content_placeholder = None
        for shape in slide.placeholders:
            if shape.placeholder_format.idx == 1:
                content_placeholder = shape
                break

        # Add bullet points
        if content_placeholder:
            content_placeholder.text = "\n".join([bullet.strip() for bullet in bullets])
        else:
            # Add a new text box if no content placeholder is found
            left = Inches(1)
            top = Inches(2)
            width = Inches(8)
            height = Inches(4)
            textbox = slide.shapes.add_textbox(left, top, width, height)
            text_frame = textbox.text_frame
            for bullet in bullets:
                paragraph = text_frame.add_paragraph()
                paragraph.text = bullet.strip()

    # Save the presentation
    output_file = f"{lesson_topic}_lesson.pptx"
    try:
        presentation.save(output_file)
    except Exception as e:
        return jsonify({"error": f"Error saving PowerPoint file: {str(e)}"}), 500

    # Return the generated file
    return send_file(output_file, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
