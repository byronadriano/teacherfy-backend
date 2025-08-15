# src/resource_handlers/google_slides_handler.py
import logging
from typing import Dict, Any, List, Tuple
from google.oauth2.credentials import Credentials
from .base_handler import BaseResourceHandler

logger = logging.getLogger(__name__)

class GoogleSlidesHandler(BaseResourceHandler):
    """Handler for generating Google Slides presentations for authenticated users."""
    
    def __init__(self, structured_content: List[Dict[str, Any]], credentials: Credentials, **kwargs):
        super().__init__(structured_content, **kwargs)
        self.credentials = credentials
        logger.info(f"GoogleSlidesHandler initialized for authenticated user")
    
    def generate(self) -> Tuple[str, str]:
        """
        Generate Google Slides presentation and return (presentation_url, presentation_id).
        Unlike other handlers that return file paths, this returns web URLs.
        """
        from src.google_slides_generator import create_google_slides_presentation
        
        logger.info(f"Creating Google Slides presentation with {len(self.structured_content)} slides")
        
        # Convert agent-based structured content to Google Slides format
        google_slides_content = self._convert_to_google_slides_format(self.structured_content)
        
        # Create the presentation using existing Google Slides generator
        presentation_url, presentation_id = create_google_slides_presentation(
            self.credentials,
            google_slides_content
        )
        
        logger.info(f"Generated Google Slides presentation: {presentation_url}")
        return presentation_url, presentation_id
    
    def _convert_to_google_slides_format(self, structured_content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert agent-based structured content to Google Slides API format.
        
        Agent format has:
        - title: str
        - content: List[str] (bullet points)
        - layout: str (optional)
        
        Google Slides format expects:
        - title: str
        - content: List[str] (for regular slides)
        - left_column/right_column: List[str] (for two-column slides)  
        - teacher_notes: List[str] (optional)
        - visual_elements: List[str] (optional)
        """
        google_slides_content = []
        
        for slide_data in structured_content:
            # Base slide structure
            google_slide = {
                "title": slide_data.get("title", "Untitled Slide"),
                "layout": self._determine_google_slides_layout(slide_data)
            }
            
            # Handle content based on layout
            layout = google_slide["layout"]
            content = slide_data.get("content", [])
            
            if layout == "TWO_COLUMNS":
                # Split content into two columns
                mid_point = len(content) // 2
                google_slide["left_column"] = content[:mid_point] if mid_point > 0 else content
                google_slide["right_column"] = content[mid_point:] if mid_point > 0 else []
            else:
                # Regular single-column content
                google_slide["content"] = content
            
            # Add teacher notes if present
            teacher_notes = slide_data.get("teacher_notes", [])
            if teacher_notes:
                google_slide["teacher_notes"] = teacher_notes
            
            # Add differentiation tips as teacher notes
            diff_tips = slide_data.get("differentiation_tips", [])
            if diff_tips:
                existing_notes = google_slide.get("teacher_notes", [])
                google_slide["teacher_notes"] = existing_notes + [f"Differentiation: {tip}" for tip in diff_tips]
            
            # Add visual elements suggestions
            visual_elements = slide_data.get("visual_elements", [])
            if visual_elements:
                google_slide["visual_elements"] = visual_elements
            
            google_slides_content.append(google_slide)
        
        logger.info(f"Converted {len(structured_content)} agent slides to Google Slides format")
        return google_slides_content
    
    def _determine_google_slides_layout(self, slide_data: Dict[str, Any]) -> str:
        """Determine appropriate Google Slides layout based on agent content."""
        # Check if slide explicitly specifies layout
        layout = slide_data.get("layout", "")
        
        if "TWO_COLUMN" in layout.upper():
            return "TWO_COLUMNS"
        
        # Check content length - use two columns for slides with many items
        content = slide_data.get("content", [])
        if len(content) > 6:  # More than 6 items might benefit from two columns
            return "TWO_COLUMNS"
        
        # Default to single column
        return "TITLE_AND_BODY"