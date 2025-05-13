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
        """Generate the worksheet docx file and return the file path"""
        # Create temp file
        temp_file = self.create_temp_file("docx")
        
        # Create a new document
        doc = docx.Document()
        
        # Add a title 
        doc.add_heading('Student Worksheet', 0)
        
        lesson_title = self.structured_content[0].get('title', 'Worksheet')
        doc.add_heading(lesson_title, 1)
        
        # Add name and date fields
        doc.add_paragraph('Name: _________________________________ Date: _________________')
        
        # Add a brief introduction based on the first slide content
        if self.structured_content and len(self.structured_content) > 0:
            first_slide = self.structured_content[0]
            intro_text = "Introduction: "
            
            if first_slide.get('content'):
                for item in first_slide.get('content', []):
                    if len(item) > 20:  # Only use substantial content
                        intro_text += item
                        break
            
            doc.add_paragraph(intro_text)
        
        # Create exercise sections from each slide
        for i, slide in enumerate(self.structured_content[1:], 1):  # Skip the title slide
            section_title = slide.get('title', f'Section {i}')
            doc.add_heading(section_title, level=2)
            
            # Add content as questions or exercises
            content = slide.get('content', [])
            
            for j, item in enumerate(content, 1):
                # Convert content into questions or activities
                if '?' in item:
                    # It's already a question
                    doc.add_paragraph(f"{j}. {item}")
                    # Add answer lines
                    doc.add_paragraph("_______________________________________________________")
                else:
                    # Convert to a prompt or question
                    doc.add_paragraph(f"{j}. Based on {section_title}, {self.create_prompt(item)}")
                    # Add answer lines
                    doc.add_paragraph("_______________________________________________________")
                    doc.add_paragraph("_______________________________________________________")
            
            # Add visual element placeholders as drawing areas or diagrams
            visual_elements = slide.get('visual_elements', [])
            if visual_elements:
                for element in visual_elements:
                    if 'diagram' in element.lower() or 'draw' in element.lower():
                        doc.add_paragraph(f"Draw: {element}")
                        # Add a drawing area (just a paragraph with a border for now)
                        p = doc.add_paragraph()
                        p.text = "[Drawing Area]"
                        # In a real implementation, you would add proper styling here
        
        # Save the document
        doc.save(temp_file)
        
        # Verify file was created and is not empty
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