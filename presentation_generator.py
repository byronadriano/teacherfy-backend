import tempfile
import os
from slide_processor import parse_outline_to_structured_content, create_presentation
import logging

logger = logging.getLogger(__name__)

def generate_presentation(outline_text, structured_content=None):
    try:
        logger.debug("Starting presentation generation")
        if structured_content is None:
            structured_content = parse_outline_to_structured_content(outline_text)
        else:
            # Ensure the content matches expected format
            structured_content = [
                {
                    'title': slide.get('title', ''),
                    'layout': slide.get('layout', 'TITLE_AND_CONTENT'),
                    'content': slide.get('content', []),
                    'teacher_notes': slide.get('teacher_notes', []),
                    'visual_elements': slide.get('visual_elements', []),
                    'left_column': slide.get('left_column', []),
                    'right_column': slide.get('right_column', [])
                }
                for slide in structured_content
            ]
        
        logger.debug(f"Creating presentation with {len(structured_content)} slides")
        prs = create_presentation(structured_content)
        
        # Save to temporary file
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f"presentation_{os.getpid()}.pptx")
        logger.debug(f"Saving presentation to {temp_file}")
        
        prs.save(temp_file)
        return temp_file
            
    except Exception as e:
        logger.error(f"Error generating presentation: {e}", exc_info=True)
        raise