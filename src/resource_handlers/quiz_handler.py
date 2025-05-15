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
    
    def generate(self) -> str:
        """Generate a quiz docx file with proper formatting for quizzes"""
        # Create temp file
        temp_file = self.create_temp_file("docx")
        
        # Create a new document
        doc = docx.Document()
        
        # Add title
        title = self.structured_content[0].get('title', 'Quiz')
        doc.add_heading(title, 0)
        
        # Add name and date fields
        doc.add_paragraph('Name: _________________________________ Date: _________________')
        
        # Add instructions
        doc.add_paragraph('Instructions: Answer the following questions to the best of your ability.')
        
        # Create question sections
        question_num = 1
        for slide in self.structured_content:
            # Skip the title slide
            if question_num == 1 and "key takeaway" in slide['title'].lower():
                continue
                
            # Add section title as heading
            doc.add_heading(slide['title'], level=2)
            
            # Process the content as questions
            for item in slide['content']:
                # Format as a question
                p = doc.add_paragraph()
                p.add_run(f"{question_num}. ").bold = True
                p.add_run(clean_text(item))
                
                # Add space for answer
                doc.add_paragraph("_______________________________________________________")
                
                question_num += 1
            
            # Add answers section if available
            if slide.get('answers'):
                # Don't add directly to the quiz - save for the answer key
                pass
        
        # Add an answer key at the end
        doc.add_page_break()
        doc.add_heading("Answer Key", level=1)
        
        # Reset question number for answer key
        question_num = 1
        for slide in self.structured_content:
            if question_num == 1 and "key takeaway" in slide['title'].lower():
                continue
                
            for item in slide['content']:
                p = doc.add_paragraph()
                p.add_run(f"{question_num}. ").bold = True
                p.add_run(clean_text(item))
                
                # Look for corresponding answer
                if slide.get('answers') and len(slide['answers']) >= question_num:
                    answer = slide['answers'][question_num - 1]
                    p = doc.add_paragraph()
                    p.add_run("   Answer: ").bold = True
                    p.add_run(clean_text(answer))
                
                question_num += 1
        
        # Save the document
        doc.save(temp_file)
        
        # Verify file exists and has content
        if not os.path.exists(temp_file):
            raise FileNotFoundError(f"Failed to create quiz file at {temp_file}")
            
        file_size = os.path.getsize(temp_file)
        logger.info(f"Generated quiz file size: {file_size} bytes")
        
        if file_size == 0:
            raise ValueError("Generated quiz file is empty")
            
        return temp_file
    
    def generate_multiple_choice_question(self, topic: str, content: str) -> Dict[str, Any]:
        """Generate a multiple choice question based on content"""
        # This is a simplified version - in a real implementation, we would use
        # more sophisticated techniques to generate good questions and distractors
        
        # Simple patterns for question generation
        if "is" in content:
            question_text = content.replace("is", "______ is")
            correct_answer = content.split("is")[0].strip()
        elif "are" in content:
            question_text = content.replace("are", "______ are")
            correct_answer = content.split("are")[0].strip()
        else:
            # Default format for other content
            question_text = f"Which of the following best describes {topic}?"
            correct_answer = content
        
        # Generate distractors (fake answers)
        distractors = [
            f"The opposite of {correct_answer}",
            f"A different aspect of {topic}",
            f"An unrelated concept to {topic}"
        ]
        
        # Create options with the correct answer in a random position
        options = {}
        option_keys = ['A', 'B', 'C', 'D']
        correct_position = random.randint(0, 3)
        
        for i, key in enumerate(option_keys):
            if i == correct_position:
                options[key] = correct_answer
            else:
                options[key] = distractors.pop(0)
        
        return {
            'question': question_text,
            'options': options,
            'correct': option_keys[correct_position]
        }
    
    def generate_short_answer_question(self, topic: str, content: str) -> str:
        """Generate a short answer question based on content"""
        # Simple patterns for question generation
        if "defined as" in content.lower() or "refers to" in content.lower():
            return f"Define or explain {topic}."
        elif "example" in content.lower() or "instance" in content.lower():
            return f"Provide an example of {topic}."
        else:
            return f"Explain the importance of {topic} in relation to {content.split()[0]}."