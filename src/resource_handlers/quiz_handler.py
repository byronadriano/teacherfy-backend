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
    
    def _extract_questions_and_answers(self, content_items, all_content_text=""):
        """
        Extract questions and answers from mixed content more intelligently
        
        Args:
            content_items: List of content items
            all_content_text: Full text content for context (optional)
            
        Returns:
            tuple: (questions, answers)
        """
        questions = []
        answers = []
        
        # Check if we have an explicit "Answers:" section
        answer_section_index = -1
        for i, item in enumerate(content_items):
            if item.strip().lower() == "answers:" or item.lower().startswith("answers:"):
                answer_section_index = i
                break
        
        if answer_section_index > 0:
            # We have an explicit split between questions and answers
            questions = [item.strip() for item in content_items[:answer_section_index] 
                        if item.strip() and not item.strip().lower() == "questions:" 
                        and not item.strip().lower().startswith("questions:")]
                        
            answers = [item.strip() for item in content_items[answer_section_index+1:] 
                      if item.strip()]
            
            return questions, answers
        
        # No explicit marker, try to detect by format
        # Common patterns for questions: numbers followed by period, question marks
        # Common patterns for answers: A., B., C., or Answer: prefixes
        
        current_section = "questions"  # Start assuming questions
        
        # Check entire content for markers
        if "answer key" in all_content_text.lower() or "answers:" in all_content_text.lower():
            # This suggests there are separate sections, but we didn't find the marker
            # in the exact content items, so let's be more aggressive
            for item in content_items:
                if re.match(r'^answi?er\s*\d+:', item.lower()) or item.lower().startswith('answer:'):
                    # Likely an answer item
                    answers.append(item)
                # Numbered items are likely questions
                elif re.match(r'^\d+\.\s', item) or item.endswith('?'):
                    questions.append(item)
                # Items starting with letters+period are likely multiple choice options or answers
                elif re.match(r'^[A-D]\.\s', item):
                    # Could be multiple choice options or answers
                    if current_section == "questions":
                        questions.append(item)
                    else:
                        answers.append(item)
                elif item.lower().startswith('correct answer') or item.lower().startswith('key:'):
                    current_section = "answers"
                    answers.append(item)
                else:
                    # Other content - add to current section
                    if current_section == "questions":
                        questions.append(item)
                    else:
                        answers.append(item)
        else:
            # No clear delineation, treat all as questions
            questions = [item for item in content_items if item.strip()]
        
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
        
        # Check for embedded sections vs. separate sections
        sections = []
        
        if len(self.structured_content) == 1 and len(self.structured_content[0].get('content', [])) > 0:
            # We likely have embedded sections in a single content item
            main_item = self.structured_content[0]
            
            # Combine all content text for analysis
            all_content_text = "\n".join(main_item.get('content', []))
            
            # Look for section headers
            section_matches = list(re.finditer(r"(?:^|\n)(?:\*\*)?Section\s+(\d+):\s*([^\n*]+)(?:\*\*)?", all_content_text))
            
            if section_matches:
                # We have properly structured sections embedded in the content
                logger.info(f"Found {len(section_matches)} embedded sections in quiz content")
                
                for i, match in enumerate(section_matches):
                    section_num = match.group(1)
                    section_title = match.group(2).strip()
                    
                    # Get the content between this section and the next
                    start_pos = match.end()
                    end_pos = all_content_text.find(f"Section {int(section_num) + 1}:", start_pos)
                    if end_pos == -1:
                        # Last section
                        section_content = all_content_text[start_pos:]
                    else:
                        section_content = all_content_text[start_pos:end_pos]
                    
                    # Extract content items
                    section_lines = [line.strip() for line in section_content.split('\n') if line.strip()]
                    
                    # Split into questions and answers
                    questions, answers = self._extract_questions_and_answers(section_lines, section_content)
                    
                    sections.append({
                        'title': section_title,
                        'questions': questions,
                        'answers': answers
                    })
            else:
                # No clear section headers, create a single section
                questions, answers = self._extract_questions_and_answers(
                    main_item.get('content', []),
                    "\n".join(main_item.get('content', []))
                )
                
                sections.append({
                    'title': 'Quiz Questions',
                    'questions': questions,
                    'answers': answers
                })
        else:
            # Process each structured section separately
            for item in self.structured_content:
                # Get answers field if it exists
                answers = item.get('answers', [])
                
                # If no specific answers field, try to extract from content
                if not answers:
                    questions, extracted_answers = self._extract_questions_and_answers(
                        item.get('content', []),
                        "\n".join(item.get('content', []))
                    )
                    
                    sections.append({
                        'title': item.get('title', 'Quiz Questions'),
                        'questions': questions,
                        'answers': extracted_answers
                    })
                else:
                    # We have a dedicated answers field
                    sections.append({
                        'title': item.get('title', 'Quiz Questions'),
                        'questions': item.get('content', []),
                        'answers': answers
                    })
        
        # Now generate the quiz document with questions
        question_num = 1
        
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
        for section in sections:
            # Add section heading
            doc.add_heading(section['title'], level=1)
            
            # Add each question with space for answers
            for question in section['questions']:
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
        
        # Add answer key section after a page break
        doc.add_page_break()
        doc.add_heading("Answer Key", level=1)
        
        # Reset question counter for answers
        question_num = 1
        
        # Now add the answer key by section
        for section in sections:
            # Add section heading
            doc.add_heading(section['title'], level=2)
            
            # Track which questions we've provided answers for
            answered_questions = set()
            
            # Add explicit answers if available
            if section['answers']:
                for answer in section['answers']:
                    if not answer.strip():
                        continue
                        
                    p = doc.add_paragraph()
                    
                    # Format based on answer style
                    if re.match(r'^\d+\.', answer):
                        # Already numbered answer
                        p.add_run(answer)
                        answered_questions.add(int(answer.split('.')[0]))
                    elif answer.lower().startswith('answer') and ':' in answer:
                        # Answer with question reference
                        p.add_run(answer)
                        # Try to extract question number
                        match = re.search(r'answer\s+(?:to\s+)?(?:question\s+)?(\d+)', answer.lower())
                        if match:
                            answered_questions.add(int(match.group(1)))
                    else:
                        # Generic answer
                        p.add_run(answer)
            
            # For questions without explicit answers, add placeholders
            if not section['answers'] or len(answered_questions) < len(section['questions']):
                for i, question in enumerate(section['questions']):
                    q_num = None
                    
                    # Try to extract question number
                    match = re.match(r'^(\d+)\.', question)
                    if match:
                        q_num = int(match.group(1))
                    else:
                        # If no explicit numbering, use position
                        q_num = i + 1
                    
                    # Only add if we don't have an answer yet
                    if q_num not in answered_questions and not re.match(r'^[A-D]\.', question):
                        p = doc.add_paragraph()
                        p.add_run(f"Question {q_num}: ").bold = True
                        
                        # Add answer placeholder for teacher to fill in
                        if question.endswith('?'):
                            p.add_run("___________________")
        
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