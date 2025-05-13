# src/resource_handlers/quiz_handler.py
import os
import logging
import docx
import random
from typing import Dict, Any, List, Optional
from .base_handler import BaseResourceHandler

logger = logging.getLogger(__name__)

class QuizHandler(BaseResourceHandler):
    """Handler for generating quizzes as Word documents"""
    
    def generate(self) -> str:
        """Generate the quiz docx file and return the file path"""
        # Create temp file
        temp_file = self.create_temp_file("docx")
        
        # Create a new document
        doc = docx.Document()
        
        # Add a title
        lesson_title = self.structured_content[0].get('title', 'Quiz')
        doc.add_heading(f"Quiz: {lesson_title}", 0)
        
        # Add name and date fields
        doc.add_paragraph('Name: _________________________________ Date: _________________')
        
        # Add instructions
        doc.add_paragraph('Instructions: Answer the following questions based on the lesson material.')
        
        question_num = 1
        
        # Extract key content from all slides to create questions
        multiple_choice_questions = []
        short_answer_questions = []
        
        for slide in self.structured_content[1:]:  # Skip the title slide
            title = slide.get('title', '')
            content_items = slide.get('content', [])
            
            # Process each content item into potential questions
            for item in content_items:
                if len(item) < 10:  # Skip very short items
                    continue
                    
                # Decide on question type - alternate between multiple choice and short answer
                if random.choice([True, False]):
                    multiple_choice_questions.append({
                        'topic': title,
                        'content': item
                    })
                else:
                    short_answer_questions.append({
                        'topic': title,
                        'content': item
                    })
        
        # Generate multiple choice questions
        doc.add_heading('Multiple Choice Questions', level=1)
        for i, q_data in enumerate(multiple_choice_questions[:5], 1):  # Limit to 5 questions
            topic = q_data['topic']
            content = q_data['content']
            
            # Generate question text
            question = self.generate_multiple_choice_question(topic, content)
            
            # Add to document
            doc.add_paragraph(f"{question_num}. {question['question']}")
            
            # Add options
            for option in ['A', 'B', 'C', 'D']:
                doc.add_paragraph(f"    {option}. {question['options'][option]}")
                
            question_num += 1
        
        # Generate short answer questions
        doc.add_heading('Short Answer Questions', level=1)
        for i, q_data in enumerate(short_answer_questions[:5], 1):  # Limit to 5 questions
            topic = q_data['topic']
            content = q_data['content']
            
            # Generate question text
            question = self.generate_short_answer_question(topic, content)
            
            # Add to document
            doc.add_paragraph(f"{question_num}. {question}")
            # Add answer lines
            doc.add_paragraph("_______________________________________________________")
            doc.add_paragraph("_______________________________________________________")
            
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