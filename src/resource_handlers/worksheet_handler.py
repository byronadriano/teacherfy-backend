# src/resource_handlers/worksheet_handler.py
import os
import logging
import docx
from typing import Dict, Any, List, Optional
from .base_handler import BaseResourceHandler

logger = logging.getLogger(__name__)

class WorksheetHandler(BaseResourceHandler):
    """Handler for generating worksheets as Word documents"""
    
    def generate(self) -> str:
        """Generate a worksheet docx file that properly uses instructions"""
        # Create temp file
        temp_file = self.create_temp_file("docx")
        
        # Create a new document
        doc = docx.Document()
        
        # Get title from first slide or use default
        worksheet_title = self.structured_content[0].get('title', 'Worksheet')
        doc.add_heading(worksheet_title, 0)
        
        # Add name and date fields
        doc.add_paragraph('Name: _________________________________ Date: _________________')
        
        # Process each section
        for section in self.structured_content[1:]:  # Skip title slide
            # Add section title
            doc.add_heading(section.get('title', 'Section'), level=1)
            
            # Add instructions if available
            if section.get('instructions'):
                p = doc.add_paragraph()
                p.add_run('Instructions: ').bold = True
                p.add_run(' '.join(section.get('instructions')))
            
            # Add content/questions
            for i, item in enumerate(section.get('content', []), 1):
                p = doc.add_paragraph()
                p.add_run(f"{i}. ").bold = True
                p.add_run(item)
                
                # Add space for answers
                doc.add_paragraph("_______________________________________________________")
                
                # For drawing activities, add more space
                if "draw" in item.lower() or "dibuja" in item.lower():
                    doc.add_paragraph("_______________________________________________________")
                    doc.add_paragraph("_______________________________________________________")
        
        # Save the document
        doc.save(temp_file)
        
        # Verify file exists and has content
        if not os.path.exists(temp_file):
            raise FileNotFoundError(f"Failed to create worksheet file at {temp_file}")
            
        file_size = os.path.getsize(temp_file)
        logger.info(f"Generated worksheet file size: {file_size} bytes")
        
        if file_size == 0:
            raise ValueError("Generated worksheet file is empty")
            
        return temp_file
    
    def create_prompt(self, content_item: str) -> str:
        """Convert a content item into a worksheet prompt/question"""
        # Simple conversion rules
        if content_item.startswith("- "):
            content_item = content_item[2:]
            
        # Create different question types
        if "define" in content_item.lower() or "definition" in content_item.lower():
            return f"Define the following term: {content_item}"
        elif "example" in content_item.lower():
            return f"Provide an example of: {content_item}"
        else:
            return f"Explain the following concept: {content_item}"