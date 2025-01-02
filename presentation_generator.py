import tempfile
from slide_processor import parse_outline_to_structured_content, create_presentation

def generate_presentation(outline_text):
    """
    Generate a PowerPoint presentation from the outline text
    """
    # Parse the outline into structured data
    structured_content = parse_outline_to_structured_content(outline_text)
    
    # Create the presentation
    prs = create_presentation(structured_content)
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as tmp:
        prs.save(tmp.name)
        tmp.seek(0)
        return tmp.name