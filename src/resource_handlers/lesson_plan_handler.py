# src/resource_handlers/lesson_plan_handler.py
import os
import logging
import docx
from typing import Dict, Any, List
from .base_handler import BaseResourceHandler

logger = logging.getLogger(__name__)

class LessonPlanHandler(BaseResourceHandler):
    """Handler for generating lesson plans as Word documents"""

    def generate(self) -> str:
        """Generate the lesson plan docx file and return the file path"""
        # Create temp file
        temp_file = self.create_temp_file("docx")
        
        # Create a new document
        doc = docx.Document()
        
        # Add a title
        lesson_title = self.structured_content[0].get('title', 'Lesson Plan')
        doc.add_heading(lesson_title, 0)
        
        # Add objectives section
        doc.add_heading('Learning Objectives', level=1)
        objectives = []
        for slide in self.structured_content:
            content = slide.get('content', [])
            for item in content:
                if 'objective' in item.lower() or 'able to' in item.lower():
                    objectives.append(item)
        
        if objectives:
            for objective in objectives:
                p = doc.add_paragraph()
                p.add_run('• ').bold = True
                p.add_run(objective)
        else:
            doc.add_paragraph('No specific objectives found.')
                
        # Add materials section
        doc.add_heading('Materials', level=1)
        materials = []
        for slide in self.structured_content:
            visual_elements = slide.get('visual_elements', [])
            for element in visual_elements:
                if any(term in element.lower() for term in ['material', 'supply', 'resource', 'handout']):
                    materials.append(element)
        
        if materials:
            for material in materials:
                p = doc.add_paragraph()
                p.add_run('• ').bold = True
                p.add_run(material)
        else:
            doc.add_paragraph('Standard classroom materials.')
            
        # Add procedure section with details from each slide
        doc.add_heading('Procedure', level=1)
        
        for i, slide in enumerate(self.structured_content):
            title = slide.get('title', f'Section {i+1}')
            doc.add_heading(title, level=2)
            
            # Add duration if available
            if slide.get('duration'):
                p = doc.add_paragraph()
                p.add_run('Duration: ').bold = True
                p.add_run(slide.get('duration'))
            
            # Add content
            content = slide.get('content', [])
            if content:
                doc.add_paragraph('Content:')
                for item in content:
                    p = doc.add_paragraph()
                    p.add_run('• ').bold = True
                    p.add_run(item)
            
            # Add procedure steps
            procedure = slide.get('procedure', [])
            if procedure:
                doc.add_paragraph('Procedure:')
                for step in procedure:
                    p = doc.add_paragraph()
                    p.add_run('• ').bold = True
                    p.add_run(step)
        
        # Add teacher notes section
        doc.add_heading('Teacher Notes and Assessment', level=1)
        for i, slide in enumerate(self.structured_content):
            if slide.get('teacher_notes'):
                doc.add_heading(slide.get('title', f'Section {i+1}'), level=2)
                
                for note in slide.get('teacher_notes'):
                    p = doc.add_paragraph()
                    p.add_run('• ').bold = True
                    p.add_run(note)
        
        # Save the document
        doc.save(temp_file)
        
        # Verify file was created and is not empty
        if not os.path.exists(temp_file):
            raise FileNotFoundError(f"Failed to create lesson plan file at {temp_file}")
            
        file_size = os.path.getsize(temp_file)
        logger.info(f"Generated lesson plan file size: {file_size} bytes")
        
        if file_size == 0:
            raise ValueError("Generated lesson plan file is empty")
            
        return temp_file