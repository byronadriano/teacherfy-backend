import tempfile
from slide_processor import parse_outline_to_structured_content, create_presentation
from openai import OpenAI
import requests
import io
from PIL import Image
import os
from datetime import datetime, timedelta
import json
import threading
from pathlib import Path

class ImageGenerationTracker:
    def __init__(self, max_daily_images=50, max_cost_per_presentation=0.20):
        self.max_daily_images = max_daily_images
        self.max_cost_per_presentation = max_cost_per_presentation
        self.cost_per_image = 0.04  # DALL-E 3 1024x1024 standard quality
        self.lock = threading.Lock()
        self.usage_file = Path("image_generation_usage.json")
        self.load_usage()

    def load_usage(self):
        try:
            if self.usage_file.exists():
                with open(self.usage_file) as f:
                    self.usage = json.load(f)
            else:
                self.usage = {"date": datetime.now().strftime("%Y-%m-%d"), "count": 0, "cost": 0.0}
        except:
            self.usage = {"date": datetime.now().strftime("%Y-%m-%d"), "count": 0, "cost": 0.0}

    def save_usage(self):
        with open(self.usage_file, "w") as f:
            json.dump(self.usage, f)

    def can_generate_images(self, num_images):
        with self.lock:
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # Reset counter if it's a new day
            if current_date != self.usage["date"]:
                self.usage = {"date": current_date, "count": 0, "cost": 0.0}
            
            # Check daily limit
            if self.usage["count"] + num_images > self.max_daily_images:
                return False, "Daily image generation limit reached"
            
            # Check cost limit for this presentation
            estimated_cost = num_images * self.cost_per_image
            if estimated_cost > self.max_cost_per_presentation:
                return False, f"Cost limit exceeded. Estimated cost: ${estimated_cost:.2f}"
            
            return True, None

    def record_generation(self, num_images):
        with self.lock:
            self.usage["count"] += num_images
            self.usage["cost"] += num_images * self.cost_per_image
            self.save_usage()

def generate_image_from_description(visual_description, client, tracker):
    """Generate an image using DALL-E based on the visual description"""
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=f"Create an educational illustration of: {visual_description}. Make it clear, simple, and suitable for a presentation.",
            size="1024x1024",
            quality="standard",
            n=1
        )
        
        # Download the generated image
        image_url = response.data[0].url
        image_response = requests.get(image_url)
        
        # Create temp file for the image
        temp_image = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        with open(temp_image.name, 'wb') as f:
            f.write(image_response.content)
        
        # Record successful generation
        tracker.record_generation(1)
            
        return temp_image.name
    except Exception as e:
        print(f"Error generating image for '{visual_description}': {e}")
        return None

def generate_presentation(outline_text, structured_content=None, language="English"):
    """Generate a PowerPoint presentation from the outline text and structured content"""
    try:
        if structured_content is None:
            structured_content = parse_outline_to_structured_content(outline_text)
        
        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Initialize tracker
        tracker = ImageGenerationTracker()
        
        # Count total visual elements needed
        total_visuals = sum(len(slide.get('visual_elements', [])) for slide in structured_content)
        
        # Check if we can generate all images
        can_generate, message = tracker.can_generate_images(total_visuals)
        if not can_generate:
            print(f"Warning: {message}. Proceeding without images.")
            return create_presentation(structured_content)
        
        # Generate images for visual elements
        for slide in structured_content:
            if slide['visual_elements']:
                slide['generated_images'] = []
                for visual in slide['visual_elements']:
                    image_path = generate_image_from_description(visual, client, tracker)
                    if image_path:
                        slide['generated_images'].append(image_path)
        
        # Create presentation with images
        prs = create_presentation(structured_content)
        
        # Clean up temporary image files
        for slide in structured_content:
            if 'generated_images' in slide:
                for image_path in slide['generated_images']:
                    try:
                        os.unlink(image_path)
                    except:
                        pass
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as tmp:
            prs.save(tmp.name)
            return tmp.name
            
    except Exception as e:
        print(f"Error generating presentation: {e}")
        raise