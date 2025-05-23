# src/resource_handlers/worksheet_handler.py - FIXED VERSION
import os
import logging
import docx
import re
from typing import Dict, Any, List, Optional
from .base_handler import BaseResourceHandler

logger = logging.getLogger(__name__)

def clean_text_for_worksheet(text):
    """Clean up text specifically for worksheet generation"""
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

def extract_question_and_answer(text):
    """Extract question and answer from text, separating them cleanly"""
    if not text or not isinstance(text, str):
        return text, None
    
    cleaned_text = clean_text_for_worksheet(text)
    
    # Look for (Answer: ...) pattern
    answer_match = re.search(r'\(Answer:\s*([^)]+)\)', cleaned_text, re.IGNORECASE)
    if answer_match:
        answer = answer_match.group(1).strip()
        # Remove the answer from the question
        question = re.sub(r'\s*\(Answer:\s*[^)]+\)', '', cleaned_text, flags=re.IGNORECASE).strip()
        return question, answer
    
    return cleaned_text, None

def extract_questions_from_content(content_list):
    """Extract and separate questions from content, filtering out teacher notes"""
    questions = []
    answers = []
    
    for item in content_list:
        if not item.strip():
            continue
        
        # Skip teacher guidance content
        item_lower = item.lower()
        if any(keyword in item_lower for keyword in [
            'differentiation tip:', 'teacher note:', 'teacher action:', 
            'assessment check:', 'instructions:'
        ]):
            continue
            
        # Skip section headers and content labels
        if (item_lower.startswith(('content:', 'questions:', 'section')) or 
            item in ['---', '', 'Content']):
            continue
        
        question, answer = extract_question_and_answer(item)
        if question:
            questions.append(question)
            if answer:
                answers.append(answer)
    
    return questions, answers

def extract_teacher_guidance(content_list):
    """Extract teacher notes and differentiation tips from content"""
    teacher_notes = []
    differentiation_tips = []
    
    for item in content_list:
        if not item or not isinstance(item, str):
            continue
            
        item_clean = clean_text_for_worksheet(item)
        item_lower = item_clean.lower()
        
        if item_lower.startswith('differentiation tip:'):
            tip = item_clean.replace('Differentiation tip:', '').replace('differentiation tip:', '').strip()
            if tip:
                differentiation_tips.append(tip)
        elif item_lower.startswith('teacher note:'):
            note = item_clean.replace('Teacher note:', '').replace('teacher note:', '').strip()
            if note:
                teacher_notes.append(note)
        elif item_lower.startswith('teacher action:'):
            action = item_clean.replace('Teacher action:', '').replace('teacher action:', '').strip()
            if action:
                teacher_notes.append(action)
    
    return teacher_notes, differentiation_tips

class WorksheetHandler(BaseResourceHandler):
    """Handler for generating worksheets as Word documents with properly separated content"""
    
    def generate(self) -> str:
        """Generate a worksheet docx file with clean separation of student and teacher content"""
        # Create temp file
        temp_file = self.create_temp_file("docx")
        
        # Create a new document
        doc = docx.Document()
        
        # Add title - use first section title or default
        worksheet_title = "Worksheet"
        if self.structured_content and len(self.structured_content) > 0:
            raw_title = self.structured_content[0].get('title', 'Worksheet')
            worksheet_title = clean_text_for_worksheet(raw_title)
        
        doc.add_heading(worksheet_title, 0)
        
        # Add name and date fields
        name_date_para = doc.add_paragraph()
        name_date_para.add_run('Name: ').bold = True
        name_date_para.add_run('_' * 40)
        name_date_para.add_run('    Date: ').bold = True
        name_date_para.add_run('_' * 20)
        
        doc.add_paragraph()  # Add spacing
        
        # STUDENT SECTION
        student_heading = doc.add_heading("STUDENT SECTION", 1)
        student_heading.alignment = docx.enum.text.WD_ALIGN_PARAGRAPH.CENTER
        
        # Add general instructions
        instructions_para = doc.add_paragraph()
        instructions_para.add_run('Instructions: ').bold = True
        instructions_para.add_run('Read each question carefully and provide your answer in the space provided.')
        
        doc.add_paragraph()  # Add some space
        
        # Process each section and extract questions
        question_counter = 1
        all_teacher_data = []  # Collect all teacher guidance for the answer key
        
        for section_idx, section in enumerate(self.structured_content):
            section_title = clean_text_for_worksheet(section.get('title', f'Section {section_idx + 1}'))
            
            # Skip if this is just a title section with no content
            if not section.get('content'):
                continue
            
            # Extract questions, answers, and teacher guidance
            questions, answers = extract_questions_from_content(section.get('content', []))
            teacher_notes, differentiation_tips = extract_teacher_guidance(section.get('content', []))
            
            # Add any teacher_notes from the structured content
            if section.get('teacher_notes'):
                for note in section.get('teacher_notes'):
                    clean_note = clean_text_for_worksheet(note)
                    if clean_note and not clean_note.lower().startswith(('differentiation', 'teacher')):
                        teacher_notes.append(clean_note)
            
            # Store teacher data for later use
            all_teacher_data.append({
                'section_title': section_title,
                'questions': questions.copy(),
                'answers': answers.copy(),
                'teacher_notes': teacher_notes.copy(),
                'differentiation_tips': differentiation_tips.copy(),
                'start_question_num': question_counter
            })
            
            if not questions:
                continue
            
            # Add section heading for students
            section_heading = doc.add_heading(section_title, level=2)
            
            # Add questions only (no answers, no teacher notes)
            for question in questions:
                # Add the question with proper numbering
                question_para = doc.add_paragraph()
                question_para.add_run(f"{question_counter}. ").bold = True
                question_para.add_run(question)
                
                # Add answer space
                if question.endswith('?'):
                    # For questions, add a line for answers
                    doc.add_paragraph("Answer: " + "_" * 50)
                else:
                    # For fill-in-the-blank or calculation problems
                    doc.add_paragraph("_" * 60)
                
                doc.add_paragraph()  # Add spacing between questions
                question_counter += 1
        
        # TEACHER SECTION - Start on new page
        doc.add_page_break()
        teacher_heading = doc.add_heading("TEACHER GUIDE & ANSWER KEY", 1)
        teacher_heading.alignment = docx.enum.text.WD_ALIGN_PARAGRAPH.CENTER
        
        # Add teacher guidance and answers by section
        for section_data in all_teacher_data:
            if not section_data['questions']:  # Skip sections with no questions
                continue
            
            # Section heading
            doc.add_heading(section_data['section_title'], level=2)
            
            # Questions and Answers
            if section_data['questions'] and section_data['answers']:
                doc.add_heading("Questions & Answers", level=3)
                
                current_q_num = section_data['start_question_num']
                for i, question in enumerate(section_data['questions']):
                    # Question
                    q_para = doc.add_paragraph()
                    q_para.add_run(f"Q{current_q_num}: ").bold = True
                    q_para.add_run(question)
                    
                    # Answer
                    if i < len(section_data['answers']):
                        a_para = doc.add_paragraph()
                        a_para.add_run("Answer: ").bold = True
                        a_para.add_run(section_data['answers'][i])
                    else:
                        a_para = doc.add_paragraph()
                        a_para.add_run("Answer: ").bold = True
                        a_para.add_run("(Teacher to provide)")
                    
                    doc.add_paragraph()  # Spacing
                    current_q_num += 1
            
            # Teaching Notes
            if section_data['teacher_notes']:
                doc.add_heading("Teaching Notes", level=3)
                for note in section_data['teacher_notes']:
                    note_para = doc.add_paragraph()
                    note_para.add_run("• ").bold = True
                    note_para.add_run(note)
            
            # Differentiation Tips
            if section_data['differentiation_tips']:
                doc.add_heading("Differentiation Tips", level=3)
                for tip in section_data['differentiation_tips']:
                    tip_para = doc.add_paragraph()
                    tip_para.add_run("• ").bold = True
                    tip_para.add_run(tip)
            
            # Add spacing between sections
            doc.add_paragraph()
        
        # Save the document
        doc.save(temp_file)
        
        # Verify file was created
        if not os.path.exists(temp_file):
            raise FileNotFoundError(f"Failed to create worksheet file at {temp_file}")
            
        file_size = os.path.getsize(temp_file)
        logger.info(f"Generated worksheet file size: {file_size} bytes")
        
        if file_size == 0:
            raise ValueError("Generated worksheet file is empty")
            
        return temp_file