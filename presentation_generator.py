import tempfile
from slide_processor import parse_outline_to_structured_content, create_presentation

def generate_presentation(outline_text, structured_content=None):
    """
    Generate a PowerPoint presentation from the outline text and structured content
    """
    if structured_content:
        # Use the provided structured content
        prs = create_presentation(structured_content)
    else:
        # Fallback to parsing the outline text if no structured content provided
        structured_content = parse_outline_to_structured_content(outline_text)
        prs = create_presentation(structured_content)
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as tmp:
        prs.save(tmp.name)
        tmp.seek(0)
        return tmp.name