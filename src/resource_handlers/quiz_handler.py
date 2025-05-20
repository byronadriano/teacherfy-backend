# src/resource_handlers/quiz_handler.py
import os
import logging
import docx
import random
from typing import Dict, Any, List, Optional
from .base_handler import BaseResourceHandler
import re

logger = logging.getLogger(__name__)

def clean_text(text):
    """Clean up text for document output"""
    if not text:
        return ""
    
    # Remove markdown formatting
    text = text.replace('**', '').replace('*', '')
    
    # Remove bullet points
    text = re.sub(r'^[-•*]\s*', '', text)
    
    # Remove numbering
    text = re.sub(r'^\d+\.\s*', '', text)
    
    return text.strip()
class QuizHandler(BaseResourceHandler):
    """Handler for generating quizzes as Word documents"""
    
    def _extract_questions_and_answers(self, content):
        """Extract questions and answers from mixed content"""
        questions = []
        answers = []
        
        # Track if we're in an answer section
        in_answer_section = False
        
        for line in content:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Check if this is an "Answers:" marker
            if line.lower() == "answers:" or line.lower().startswith("answers:"):
                in_answer_section = True
                continue
                
            # If we're in the answer section, collect answers
            if in_answer_section:
                answers.append(line)
            else:
                # Otherwise it's a question
                questions.append(line)
        
        return questions, answers
    
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
        
        # Add instructions
        doc.add_paragraph('Instructions: Answer the following questions to the best of your ability.')
        
        # Now we need to separate questions from answers across all sections
        all_questions = []
        all_answers = []
        
        # Process each section
        for section in self.structured_content:
            # Get this section's title
            section_title = section.get('title', '')
            
            # Get content items
            content_items = section.get('content', [])
            
            # Extract questions and answers
            questions, answers = self._extract_questions_and_answers(content_items)
            
            # Add to our lists, with section titles
            if section_title:
                all_questions.append((section_title, questions))
                all_answers.append((section_title, questions, answers))
        
        # Now generate the quiz document with questions
        question_num = 1
        for section_title, questions in all_questions:
            # Add section heading
            doc.add_heading(section_title, level=1)
            
            # Add each question with space for answers
            for question in questions:
                p = doc.add_paragraph()
                p.add_run(f"{question_num}. ").bold = True
                p.add_run(question)
                
                # Add space for answer
                doc.add_paragraph("_______________________________________________________")
                question_num += 1
        
        # Add answer key section after a page break
        doc.add_page_break()
        doc.add_heading("Answer Key", level=1)
        
        # Now add the answer key
        question_num = 1
        for section_title, questions, answers in all_answers:
            # Add section heading
            doc.add_heading(section_title, level=2)
            
            # Add each question with its answer
            for i, question in enumerate(questions):
                p = doc.add_paragraph()
                p.add_run(f"{question_num}. ").bold = True
                p.add_run(question)
                
                # Add the corresponding answer if available
                if i < len(answers):
                    p = doc.add_paragraph()
                    p.add_run("   Answer: ").bold = True
                    p.add_run(answers[i])
                
                question_num += 1
        
        # Save the document
        doc.save(temp_file)
        
        # Verify file was created and is not empty
        if not os.path.exists(temp_file):
            raise FileNotFoundError(f"Failed to create quiz file at {temp_file}")
            
        file_size = os.path.getsize(temp_file)
        logger.info(f"Generated quiz file size: {file_size} bytes")
        
        if file_size == 0:
            raise ValueError("Generated quiz file is empty")
            
        return temp_file