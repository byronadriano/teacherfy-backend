import tempfile
import os
from src.slide_processor import parse_outline_to_structured_content, create_presentation
import logging
import json
import time

logger = logging.getLogger(__name__)

def generate_presentation(outline_text, structured_content=None):
    try:
        logger.debug("Starting presentation generation")
        
        if structured_content is None:
            logger.debug("Parsing outline text to structured content")
            structured_content = parse_outline_to_structured_content(outline_text)
        
        # Create temp file with unique name
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f"presentation_{os.getpid()}_{int(time.time())}.pptx")
        
        logger.debug(f"Creating presentation with {len(structured_content)} slides")
        prs = create_presentation(structured_content)
        
        logger.debug(f"Saving presentation to {temp_file}")
        prs.save(temp_file)
        
        # Verify file was created and is not empty
        if not os.path.exists(temp_file):
            raise FileNotFoundError("Failed to create presentation file")
            
        if os.path.getsize(temp_file) == 0:
            raise ValueError("Generated presentation file is empty")
            
        return temp_file
            
    except Exception as e:
        logger.error(f"Error generating presentation: {e}", exc_info=True)
        raise