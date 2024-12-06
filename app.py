from flask import Flask, request, jsonify, send_file
from openai import OpenAI
from pptx import Presentation
from pptx.util import Inches
import os

app = Flask(__name__)

# Initialize the OpenAI client
# This will use OPENAI_API_KEY from environment variables if set
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY")
)

@app.route("/", methods=["GET"])
def home():
    return "Welcome to Teacherfy.ai Backend!"

@app.route("/generate", methods=["POST"])
def generate_presentation():
    # Parse request data
    data = request.json
    lesson_topic = data.get("lesson_topic", "Default Topic")
    district = data.get("district", "Default District")

    # Create prompt
    prompt = f"Create 3 slide bullet points for a lesson on {lesson_topic} for {district}."

    try:
        # Generate content with OpenAI
        # Using gpt-4o-mini model as requested
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        slides_content = response.choices[0].message.content.strip().split("\n\n")
    except Exception as e:
        return jsonify({"error": f"Error generating AI content: {str(e)}"}), 500

    # Load PowerPoint template
    try:
        presentation = Presentation("templates/base_template.pptx")
    except Exception as e:
        return jsonify({"error": f"Error loading PowerPoint template: {str(e)}"}), 500

    # Create slides
    for slide_content in slides_content:
        slide = presentation.slides.add_slide(presentation.slide_layouts[1])  # adjust layout if needed
        parts = slide_content.split("\n")
        title = parts[0].strip() if parts else "Untitled Slide"
        bullets = parts[1:] if len(parts) > 1 else []

        # Add title
        if slide.shapes.title:
            slide.shapes.title.text = title

        # Find the content placeholder
        content_placeholder = None
        for shape in slide.placeholders:
            if shape.placeholder_format.idx == 1:  # typically the content placeholder
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

    # Save the presentation
    output_file = f"{lesson_topic}_lesson.pptx"
    try:
        presentation.save(output_file)
    except Exception as e:
        return jsonify({"error": f"Error saving PowerPoint file: {str(e)}"}), 500

    return send_file(output_file, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
