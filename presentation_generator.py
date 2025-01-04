import tempfile
from slide_processor import parse_outline_to_structured_content, create_presentation

# presentation_generator.py
def generate_presentation(outline_text, structured_content=None):
    """Generate a PowerPoint presentation from the outline text and structured content"""
    try:
        if structured_content is None:
            structured_content = parse_outline_to_structured_content(outline_text)
        
        # Create presentation
        prs = create_presentation(structured_content)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as tmp:
            prs.save(tmp.name)
            return tmp.name
            
    except Exception as e:
        print(f"Error generating presentation: {e}")
        raise