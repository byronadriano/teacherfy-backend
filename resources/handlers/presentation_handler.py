# resources/handlers/presentation_handler.py - CLEANED VERSION
import os
import logging
from typing import Dict, Any, List
from .base_handler import BaseResourceHandler

logger = logging.getLogger(__name__)

class PresentationHandler(BaseResourceHandler):
    """Handler for generating PowerPoint presentations with optional image support."""
    
    def __init__(self, structured_content: List[Dict[str, Any]], **kwargs):
        super().__init__(structured_content, **kwargs)
        logger.info(f"PresentationHandler initialized with images: {self.include_images}")
    
    def generate(self) -> str:
        """Generate the presentation file and return the file path."""
        # Create temp file
        temp_file = self.create_temp_file("pptx")
        
        # CRITICAL DEBUG: Log image preference at multiple levels
        logger.info(f"🎯 PresentationHandler.generate() called with include_images: {self.include_images}")
        logger.info(f"Creating presentation with {len(self.structured_content)} slides, images: {self.include_images}")
        
        # Import the restored slide processor functions
        from resources.generators.slide_processor import create_clean_presentation_with_images, create_clean_presentation
        
        # Use the correct function based on image preference with explicit logging
        if self.include_images:
            logger.info("📸 USING create_clean_presentation_with_images() - IMAGES ENABLED")
            prs = create_clean_presentation_with_images(self.structured_content, include_images=True)
        else:
            logger.info("🚫 USING create_clean_presentation() - NO IMAGES")
            prs = create_clean_presentation(self.structured_content)
        
        # Save presentation
        logger.info(f"Saving presentation to {temp_file}")
        prs.save(temp_file)
        
        # Verify file was created and is not empty
        if not os.path.exists(temp_file):
            raise FileNotFoundError(f"Failed to create presentation file at {temp_file}")
            
        file_size = os.path.getsize(temp_file)
        logger.info(f"Generated presentation file size: {file_size} bytes (images: {self.include_images})")
        
        if file_size == 0:
            raise ValueError("Generated presentation file is empty")
            
        return temp_file