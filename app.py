from flask import Flask, request, jsonify, send_file
import openai
from pptx import Presentation
import os

app = Flask(__name__)

# Load OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route("/", methods=["GET"])
def home():
    return "Welcome to Teacherfy.ai Backend!"

@app.route("/generate", methods=["POST"])
def generate_presentation():
    data = request.json
    lesson_topic = data.get("lesson_topic", "Default Topic")
    district = data.get("district", "Default District")
    
    # Use OpenAI to generate content
    prompt = f"Create 3 slide bullet points for a lesson on {lesson_topic} for {district}."
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=200
    )

    slides_content = response["choices"][0]["text"].strip().split("\n\n")
    
    # Generate PowerPoint
    presentation = Presentation("templates/base_template.pptx")
    for slide_content in slides_content:
        slide = presentation.slides.add_slide(presentation.slide_layouts[1])  # Use title + content layout
        title, *bullets = slide_content.split("\n")
        slide.shapes.title.text = title.strip()
        for bullet in bullets:
            slide.placeholders[1].text += f"- {bullet.strip()}\n"

    # Save file
    output_path = f"{lesson_topic}_lesson.pptx"
    presentation.save(output_path)
    
    return send_file(output_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
