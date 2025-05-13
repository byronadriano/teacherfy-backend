# src/resource_handlers/lesson_plan_handler.py
import os
import logging
import docx
from typing import Dict, Any, List, Optional
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
            title = slide.get('title', f'Slide {i+1}')
            doc.add_heading(title, level=2)
            
            # Add content
            content = slide.get('content', [])
            if content:
                doc.add_paragraph('Content:')
                for item in content:
                    p = doc.add_paragraph()
                    p.add_run('• ').bold = True
                    p.add_run(item)
            
            # Add teacher notes as procedure steps
            notes = slide.get('teacher_notes', [])
            if notes:
                doc.add_paragraph('Instructions:')
                for note in notes:
                    p = doc.add_paragraph()
                    p.add_run('• ').bold = True
                    p.add_run(note)
        
        # Add assessment section
        doc.add_heading('Assessment', level=1)
        assessments = []
        for slide in self.structured_content:
            notes = slide.get('teacher_notes', [])
            for note in notes:
                if 'ASSESSMENT:' in note or 'assessment' in note.lower():
                    assessments.append(note.replace('ASSESSMENT:', '').strip())
        
        if assessments:
            for assessment in assessments:
                p = doc.add_paragraph()
                p.add_run('• ').bold = True
                p.add_run(assessment)
        else:
            doc.add_paragraph('Formative assessment through questioning and observation.')
            
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