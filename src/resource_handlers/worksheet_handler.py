# src/resource_handlers/worksheet_handler.py
import os
import logging
import docx
import re
from typing import Dict, Any, List, Optional
from .base_handler import BaseResourceHandler

logger = logging.getLogger(__name__)

class WorksheetHandler(BaseResourceHandler):
    """Handler for generating worksheets as Word documents"""
    
    def generate(self) -> str:
        """Generate a quiz docx file with properly separated questions and answers"""
        # Create temp file
        temp_file = self.create_temp_file("docx")
        
        # Create a new document
        doc = docx.Document()
        
        # Add title - use first section title or default
        quiz_title = "Quiz/Test"
        if self.structured_content and len(self.structured_content) > 0:
            quiz_title = self.structured_content[0].get('title', 'Quiz/Test')
        doc.add_heading(quiz_title, 0)
        
        # Add name and date fields
        doc.add_paragraph('Name: _________________________________ Date: _________________')
        
        # STUDENT SECTION
        doc.add_heading("STUDENT SECTION", 1)
        
        # Add instructions if available
        if self.structured_content and self.structured_content[0].get('instructions'):
            p = doc.add_paragraph()
            p.add_run('Instructions: ').bold = True
            p.add_run(self.structured_content[0].get('instructions')[0])
        else:
            # Default instructions
            p = doc.add_paragraph()
            p.add_run('Instructions: ').bold = True
            p.add_run('Answer the following questions to the best of your ability.')
        
        doc.add_paragraph()  # Add some space
        
        # Add each section with questions
        question_num = 1
        for section in self.structured_content:
            # Add section heading
            doc.add_heading(section['title'], level=2)
            
            # Add each question with space for answers
            for question in section.get('content', []):
                cleaned_question = question.strip()
                
                # Skip empty items and section headers
                if not cleaned_question or cleaned_question.lower() == "questions:" or cleaned_question.lower().startswith("questions:"):
                    continue
                
                # Handle different question formats
                if re.match(r'^\d+\.', cleaned_question):
                    # Already numbered
                    p = doc.add_paragraph()
                    p.add_run(cleaned_question)
                elif cleaned_question.endswith('?'):
                    # It's a question without numbering
                    p = doc.add_paragraph()
                    p.add_run(f"{question_num}. ").bold = True
                    p.add_run(cleaned_question)
                    question_num += 1
                elif re.match(r'^[A-D]\.', cleaned_question):
                    # Multiple choice option
                    p = doc.add_paragraph()
                    p.add_run(f"    {cleaned_question}")  # Indent options
                else:
                    # Other content
                    p = doc.add_paragraph()
                    p.add_run(cleaned_question)
                
                # Add space for answer if this isn't a multiple choice option
                if not re.match(r'^[A-D]\.', cleaned_question) and cleaned_question.endswith('?'):
                    doc.add_paragraph("_______________________________________________________")
        
        # TEACHER SECTION
        doc.add_page_break()
        doc.add_heading("TEACHER GUIDE: ANSWER KEY", 1)
        
        # Now add the answer key by section
        for section in self.structured_content:
            # Add section heading
            doc.add_heading(section['title'], level=2)
            
            # Add answers and teacher notes
            if section.get('answers'):
                doc.add_heading("Answers", level=3)
                for answer in section.get('answers'):
                    if not answer.strip():
                        continue
                    p = doc.add_paragraph()
                    p.add_run(f"• {answer}")
            
            if section.get('teacher_notes'):
                doc.add_heading("Teacher Notes", level=3)
                for note in section.get('teacher_notes'):
                    if not note.strip():
                        continue
                    p = doc.add_paragraph()
                    p.add_run(f"• {note}")
        
        # Save the document
        doc.save(temp_file)
        
        # Verify file was created
        if not os.path.exists(temp_file):
            raise FileNotFoundError(f"Failed to create quiz file at {temp_file}")
            
        file_size = os.path.getsize(temp_file)
        logger.info(f"Generated quiz file size: {file_size} bytes")
        
        if file_size == 0:
            raise ValueError("Generated quiz file is empty")
            
        return temp_file