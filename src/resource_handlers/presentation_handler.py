# src/resource_handlers/presentation_handler.py
import os
import logging
from typing import Dict, Any, List, Optional
from .base_handler import BaseResourceHandler
from src.slide_processor import create_presentation

logger = logging.getLogger(__name__)

class PresentationHandler(BaseResourceHandler):
    """Handler for generating PowerPoint presentations"""
    
    def generate(self) -> str:
        """Generate the presentation file and return the file path"""
        # Create temp file
        temp_file = self.create_temp_file("pptx")
        
        # Create presentation
        logger.info(f"Creating presentation with {len(self.structured_content)} slides")
        prs = create_presentation(self.structured_content)
        
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