import tempfile
import os
from src.slide_processor import parse_outline_to_structured_content, create_presentation
import logging
import json

logger = logging.getLogger(__name__)

def generate_presentation(outline_text, structured_content=None):
    """Generate a PowerPoint presentation from the outline text and structured content"""
    try:
        logger.debug("Starting presentation generation")
        if structured_content is None:
            structured_content = parse_outline_to_structured_content(outline_text)
        else:
            # Normalize the incoming structured content
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
            
            # Post-process to ensure content is properly distributed
            for slide in structured_content:
                if slide['layout'] == "TWO_COLUMN" and not (slide['left_column'] or slide['right_column']):
                    content_length = len(slide['content'])
                    mid_point = content_length // 2
                    slide['left_column'] = slide['content'][:mid_point]
                    slide['right_column'] = slide['content'][mid_point:]
                    slide['content'] = []
                    
        logger.debug(f"Received structured content: {json.dumps(structured_content, indent=2)}")
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