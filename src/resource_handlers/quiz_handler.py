# src/resource_handlers/quiz_handler.py - Updated with better text processing
import os
import logging
import docx
import random
from typing import Dict, Any, List, Optional
from .base_handler import BaseResourceHandler
import re

logger = logging.getLogger(__name__)

def clean_text_for_quiz(text):
    """Clean up text specifically for quiz generation"""
    if not text:
        return ""
    
    # Remove markdown formatting
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold** -> bold
    text = re.sub(r'\*([^*]+)\*', r'\1', text)      # *italic* -> italic
    text = re.sub(r'__([^_]+)__', r'\1', text)      # __bold__ -> bold
    text = re.sub(r'_([^_]+)_', r'\1', text)        # _italic_ -> italic
    
    # Remove section markers and dividers
    text = re.sub(r'^---+$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\*\*Section \d+:', 'Section', text, flags=re.MULTILINE)
    
    # Clean up bullet points but preserve structure
    text = re.sub(r'^[-•*]\s*', '', text, flags=re.MULTILINE)
    
    # Clean up multiple spaces and normalize whitespace
    text = ' '.join(text.split())
    
    return text.strip()

def extract_questions_from_content(content_list):
    """Extract and separate questions from content"""
    questions = []
    
    for item in content_list:
        if not item.strip():
            continue
            
        cleaned_item = clean_text_for_quiz(item)
        
        # Skip section headers and content labels
        if (cleaned_item.lower().startswith(('content:', 'questions:', 'section')) or 
            cleaned_item in ['---', '', 'Content']):
            continue
            
        questions.append(cleaned_item)
    
    return questions

class QuizHandler(BaseResourceHandler):
    """Handler for generating quizzes as Word documents with improved text processing"""
    
    def generate(self) -> str:
        """Generate a quiz docx file with properly separated questions and answers"""
        # Create temp file
        temp_file = self.create_temp_file("docx")
        
        # Create a new document
        doc = docx.Document()
        
        # Add title - use first section title or default
        quiz_title = "Quiz/Test"
        if self.structured_content and len(self.structured_content) > 0:
            raw_title = self.structured_content[0].get('title', 'Quiz/Test')
            quiz_title = clean_text_for_quiz(raw_title)
        
        doc.add_heading(quiz_title, 0)
        
        # Add name and date fields
        doc.add_paragraph('Name: _________________________________ Date: _________________')
        doc.add_paragraph()  # Add spacing
        
        # STUDENT SECTION
        doc.add_heading("STUDENT SECTION", 1)
        
        # Add instructions if available
        instructions_added = False
        for section in self.structured_content:
            if section.get('instructions'):
                instructions = section.get('instructions')
                if instructions and len(instructions) > 0:
                    p = doc.add_paragraph()
                    p.add_run('Instructions: ').bold = True
                    p.add_run(clean_text_for_quiz(instructions[0]))
                    instructions_added = True
                    break
        
        if not instructions_added:
            # Default instructions
            p = doc.add_paragraph()
            p.add_run('Instructions: ').bold = True
            p.add_run('Answer the following questions to the best of your ability.')
        
        doc.add_paragraph()  # Add some space
        
        # Process each section
        question_counter = 1
        all_answers = []  # Collect answers for answer key
        
        for section_idx, section in enumerate(self.structured_content):
            section_title = clean_text_for_quiz(section.get('title', f'Section {section_idx + 1}'))
            
            # Skip if this is just a title section
            if not section.get('content'):
                continue
                
            # Add section heading
            doc.add_heading(section_title, level=2)
            
            # Extract and process questions
            questions = extract_questions_from_content(section.get('content', []))
            section_answers = []
            
            current_question = None
            current_options = []
            
            for item in questions:
                # Check if this is a multiple choice option
                if re.match(r'^[A-D]\)\s*.+', item):
                    current_options.append(item)
                else:
                    # This is a new question
                    # First, save the previous question if it exists
                    if current_question:
                        # Add the question
                        p = doc.add_paragraph()
                        p.add_run(f"{question_counter}. ").bold = True
                        p.add_run(current_question)
                        
                        # Add options if any
                        for option in current_options:
                            doc.add_paragraph(f"    {option}")
                        
                        # Add answer space if no options (short answer)
                        if not current_options:
                            doc.add_paragraph("_______________________________________________________")
                        
                        # Store for answer key
                        section_answers.append({
                            'question_num': question_counter,
                            'question': current_question,
                            'options': current_options.copy()
                        })
                        
                        question_counter += 1
                    
                    # Start new question
                    current_question = item
                    current_options = []
            
            # Don't forget the last question
            if current_question:
                p = doc.add_paragraph()
                p.add_run(f"{question_counter}. ").bold = True
                p.add_run(current_question)
                
                for option in current_options:
                    doc.add_paragraph(f"    {option}")
                
                if not current_options:
                    doc.add_paragraph("_______________________________________________________")
                
                section_answers.append({
                    'question_num': question_counter,
                    'question': current_question,
                    'options': current_options.copy()
                })
                
                question_counter += 1
            
            # Store section answers
            all_answers.append({
                'section_title': section_title,
                'questions': section_answers,
                'teacher_notes': [clean_text_for_quiz(note) for note in section.get('teacher_notes', []) if note.strip()],
                'provided_answers': [clean_text_for_quiz(ans) for ans in section.get('answers', []) if ans.strip()]
            })
        
        # TEACHER SECTION
        doc.add_page_break()
        doc.add_heading("TEACHER GUIDE: ANSWER KEY", 1)
        
        # Add answer key by section
        for section_data in all_answers:
            if not section_data['questions']:  # Skip sections with no questions
                continue
                
            doc.add_heading(section_data['section_title'], level=2)
            
            # Add questions and space for answers
            doc.add_heading("Questions and Answer Space", level=3)
            for q_data in section_data['questions']:
                p = doc.add_paragraph()
                p.add_run(f"Question {q_data['question_num']}: ").bold = True
                p.add_run(q_data['question'])
                
                if q_data['options']:
                    doc.add_paragraph("Multiple choice options provided above.")
                
                # Add space for teacher to write correct answer
                doc.add_paragraph("Answer: _________________________________")
                doc.add_paragraph()  # Spacing
            
            # Add provided answers if any
            if section_data['provided_answers']:
                doc.add_heading("Provided Answer Key", level=3)
                for i, answer in enumerate(section_data['provided_answers']):
                    p = doc.add_paragraph()
                    p.add_run(f"• {answer}")
            
            # Add teacher notes if any
            if section_data['teacher_notes']:
                doc.add_heading("Teacher Notes", level=3)
                for note in section_data['teacher_notes']:
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