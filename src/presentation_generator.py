# src/presentation_generator.py

import tempfile
import os
import logging
import json
import time
import traceback
from src.slide_processor import parse_outline_to_structured_content, create_presentation

logger = logging.getLogger(__name__)

def generate_presentation(outline_text, structured_content=None):
    try:
        logger.info("Starting presentation generation")
        
        # Log input parameters
        logger.info(f"Outline text length: {len(outline_text) if outline_text else 0}")
        logger.info(f"Structured content: {len(structured_content) if structured_content else 0} slides")
        
        # If JSON string is provided instead of a list, attempt to parse it
        if isinstance(structured_content, str):
            logger.info("Structured content is a string, attempting to parse as JSON")
            try:
                structured_content = json.loads(structured_content)
                logger.info("Successfully parsed structured content JSON")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse structured content JSON: {e}")
                raise ValueError("Invalid structured content format: not valid JSON")
        
        # If no structured content provided, parse from outline text
        if not structured_content:
            if not outline_text:
                raise ValueError("Neither structured content nor outline text provided")
            logger.info("Parsing outline text to structured content")
            structured_content = parse_outline_to_structured_content(outline_text)
            logger.info(f"Parsed {len(structured_content)} slides from outline text")
        
        # Validate structured content
        if not isinstance(structured_content, list):
            raise ValueError(f"Structured content must be a list, got {type(structured_content).__name__}")
        
        if len(structured_content) == 0:
            raise ValueError("Structured content is empty (no slides)")
        
        # Validate each slide has the required fields
        for i, slide in enumerate(structured_content):
            if not isinstance(slide, dict):
                raise ValueError(f"Slide {i} is not a dictionary")
            
            # Check for required fields
            required_fields = ['title', 'layout']
            missing_fields = [field for field in required_fields if field not in slide]
            if missing_fields:
                raise ValueError(f"Slide {i} is missing required fields: {', '.join(missing_fields)}")
            
            # Ensure content or columns are present
            if not (slide.get('content') or (slide.get('left_column') and slide.get('right_column'))):
                logger.warning(f"Slide {i} has no content or columns")
        
        # Create temp file with unique name
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f"presentation_{os.getpid()}_{int(time.time())}.pptx")
        logger.info(f"Creating presentation file at: {temp_file}")
        
        # Create presentation
        logger.info(f"Creating presentation with {len(structured_content)} slides")
        prs = create_presentation(structured_content)
        
        # Save presentation
        logger.info(f"Saving presentation to {temp_file}")
        prs.save(temp_file)
        
        # Verify file was created and is not empty
        if not os.path.exists(temp_file):
            raise FileNotFoundError(f"Failed to create presentation file at {temp_file}")
            
        file_size = os.path.getsize(temp_file)
        logger.info(f"Generated presentation file size: {file_size} bytes")
        
        if file_size == 0:
            raise ValueError("Generated presentation file is empty")
            
        return temp_file
            
    except Exception as e:
        logger.error(f"Error generating presentation: {e}", exc_info=True)
        logger.error(f"Error traceback: {traceback.format_exc()}")
        raise