# src/resource_handlers/base_handler.py - UNIFIED VERSION
import os
import tempfile
import time
import logging
import re
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class BaseResourceHandler:
    """Unified base class for all resource handlers with common text processing."""
    
    def __init__(self, structured_content: List[Dict[str, Any]], **kwargs):
        self.structured_content = structured_content
        self.include_images = kwargs.get('include_images', False)
        logger.info(f"{self.__class__.__name__} initialized with {len(structured_content)} items")
        
        # Clean the structured content during initialization
        self.structured_content = self.prepare_content_for_handler(
            structured_content, 
            self._get_resource_type()
        )
        
    def generate(self) -> str:
        """Generate the resource file and return the file path."""
        raise NotImplementedError("Subclasses must implement this method")
    
    def create_temp_file(self, extension: str) -> str:
        """Create a temporary file with unique name."""
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f"resource_{os.getpid()}_{int(time.time())}.{extension}")
        logger.info(f"Creating temporary file at: {temp_file}")
        return temp_file
    
    def _get_resource_type(self) -> str:
        """Get the resource type from the class name."""
        class_name = self.__class__.__name__.lower()
        if 'presentation' in class_name:
            return 'PRESENTATION'
        elif 'quiz' in class_name:
            return 'QUIZ'
        elif 'worksheet' in class_name:
            return 'WORKSHEET'
        elif 'lesson' in class_name:
            return 'LESSON_PLAN'
        else:
            return 'PRESENTATION'
    
    # ===== TEXT PROCESSING METHODS =====
    
    def clean_markdown_and_formatting(self, text: str) -> str:
        """Remove all markdown formatting and clean up text for document generation."""
        if not text or not isinstance(text, str):
            return ""
        
        # Remove markdown bold/italic formatting
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold** -> bold
        text = re.sub(r'\*([^*]+)\*', r'\1', text)      # *italic* -> italic
        text = re.sub(r'__([^_]+)__', r'\1', text)      # __bold__ -> bold
        text = re.sub(r'_([^_]+)_', r'\1', text)        # _italic_ -> italic
        
        # Remove strikethrough
        text = re.sub(r'~~([^~]+)~~', r'\1', text)      # ~~strike~~ -> strike
        
        # Remove markdown headers but keep the text
        text = re.sub(r'^#{1,6}\s*(.+)$', r'\1', text, flags=re.MULTILINE)
        
        # Remove markdown links but keep the text
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # [text](url) -> text
        
        # Remove inline code backticks
        text = re.sub(r'`([^`]+)`', r'\1', text)        # `code` -> code
        
        # Remove section markers and dividers
        text = re.sub(r'^---+$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\*\*Section \d+:', '', text, flags=re.MULTILINE)
        
        # Clean up standalone asterisks
        text = re.sub(r'^\*+\s*', '', text)             # Remove leading asterisks
        text = re.sub(r'\s*\*+$', '', text)             # Remove trailing asterisks
        
        # Clean up bullet points and numbering
        text = re.sub(r'^[-•*]\s*', '', text)           # Remove bullet points
        text = re.sub(r'^\d+\.\s*', '', text)           # Remove numbering
        
        # Clean up multiple spaces and normalize whitespace
        text = ' '.join(text.split())
        
        # Remove any remaining special formatting characters
        text = text.replace('---', '')                   # Remove horizontal rules
        text = text.replace('***', '')                   # Remove emphasis combinations
        
        return text.strip()

    def clean_content_list(self, content_list: List[str]) -> List[str]:
        """Clean a list of content items, removing formatting and empty items."""
        if not content_list or not isinstance(content_list, list):
            return []
        
        cleaned_list = []
        for item in content_list:
            if isinstance(item, str):
                cleaned_item = self.clean_markdown_and_formatting(item)
                if cleaned_item:  # Only add non-empty items
                    cleaned_list.append(cleaned_item)
        
        return cleaned_list

    def extract_question_and_answer(self, text: str) -> tuple[str, Optional[str]]:
        """Extract question and answer from text, handling multiple languages."""
        if not text or not isinstance(text, str):
            return text, None
        
        cleaned_text = self.clean_markdown_and_formatting(text)
        
        # Look for multiple answer patterns (English and common translations)
        answer_patterns = [
            r'\(Answer:\s*([^)]+)\)',      # English: (Answer: ...)
            r'\(Respuesta:\s*([^)]+)\)',   # Spanish: (Respuesta: ...)
            r'\(Réponse:\s*([^)]+)\)',     # French: (Réponse: ...)
            r'\(Antwort:\s*([^)]+)\)',     # German: (Antwort: ...)
            r'\(Risposta:\s*([^)]+)\)',    # Italian: (Risposta: ...)
            r'\(答案:\s*([^)]+)\)',         # Chinese: (答案: ...)
            r'\(回答:\s*([^)]+)\)',         # Japanese: (回答: ...)
            r'\(답:\s*([^)]+)\)',          # Korean: (답: ...)
            r'\(Jawaban:\s*([^)]+)\)',     # Indonesian: (Jawaban: ...)
            r'\(Câu trả lời:\s*([^)]+)\)', # Vietnamese: (Câu trả lời: ...)
            # Handle malformed patterns where answer leaks into question text
            r'([A-D]\)) [A-Za-z0-9\s/-]+\s+([A-Za-z0-9\s/-]+\s*-\s*.+?)(?:\)|\s*$)',  # Multiple choice with leaked answer
            r'Answer:\s*([^(]+?)(?:\)|$)',  # Answer: pattern without parentheses
        ]
        
        for pattern in answer_patterns:
            answer_match = re.search(pattern, cleaned_text, re.IGNORECASE)
            if answer_match:
                answer = answer_match.group(1).strip()
                # Remove the answer from the question
                question = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE).strip()
                return question, answer
        
        return cleaned_text, None

    def extract_questions_from_content(self, content_list: List[str]) -> tuple[List[str], List[str]]:
        """Extract and separate questions from content, filtering out teacher notes."""
        questions = []
        answers = []
        
        for item in content_list:
            if not item.strip():
                continue
            
            # Skip teacher guidance content (check for multiple languages)
            item_lower = item.lower()
            teacher_keywords = [
                'differentiation tip:', 'teacher note:', 'teacher action:', 
                'assessment check:', 'instructions:',
                # Spanish
                'consejo de diferenciación:', 'nota del maestro:', 'acción del maestro:',
                # French  
                'conseil de différenciation:', 'note de l\'enseignant:', 'action de l\'enseignant:',
                # German
                'differenzierungstipp:', 'lehrernotiz:', 'lehreraktion:',
            ]
            
            if any(keyword in item_lower for keyword in teacher_keywords):
                continue
                
            # Skip section headers and content labels
            if (item_lower.startswith(('content:', 'questions:', 'section', 'contenido:', 'preguntas:')) or 
                item in ['---', '', 'Content']):
                continue
            
            question, answer = self.extract_question_and_answer(item)
            if question:
                questions.append(question)
                # Always append an answer for every question to keep lists in sync
                answers.append(answer if answer else "(Answer not provided)")
        
        return questions, answers

    def extract_teacher_guidance(self, content_list: List[str]) -> tuple[List[str], List[str]]:
        """Extract teacher notes and differentiation tips from content (multilingual)."""
        teacher_notes = []
        differentiation_tips = []
        
        for item in content_list:
            if not item or not isinstance(item, str):
                continue
                
            item_clean = self.clean_markdown_and_formatting(item)
            item_lower = item_clean.lower()
            
            # Check for differentiation tips in multiple languages
            diff_patterns = [
                (r'^differentiation tip:\s*(.+)', 'differentiation tip:'),
                (r'^consejo de diferenciación:\s*(.+)', 'consejo de diferenciación:'),
                (r'^conseil de différenciation:\s*(.+)', 'conseil de différenciation:'),
                (r'^differenzierungstipp:\s*(.+)', 'differenzierungstipp:'),
            ]
            
            # Check for teacher notes in multiple languages
            note_patterns = [
                (r'^teacher note:\s*(.+)', 'teacher note:'),
                (r'^teacher action:\s*(.+)', 'teacher action:'),
                (r'^nota del maestro:\s*(.+)', 'nota del maestro:'),
                (r'^acción del maestro:\s*(.+)', 'acción del maestro:'),
                (r'^note de l\'enseignant:\s*(.+)', 'note de l\'enseignant:'),
                (r'^action de l\'enseignant:\s*(.+)', 'action de l\'enseignant:'),
                (r'^lehrernotiz:\s*(.+)', 'lehrernotiz:'),
                (r'^lehreraktion:\s*(.+)', 'lehreraktion:'),
            ]
            
            # Check differentiation patterns
            for pattern, keyword in diff_patterns:
                match = re.search(pattern, item_lower)
                if match:
                    tip = item_clean.replace(keyword, '').replace(keyword.title(), '').strip()
                    if tip:
                        differentiation_tips.append(tip)
                    break
            
            # Check teacher note patterns
            for pattern, keyword in note_patterns:
                match = re.search(pattern, item_lower)
                if match:
                    note = item_clean.replace(keyword, '').replace(keyword.title(), '').strip()
                    if note:
                        teacher_notes.append(note)
                    break
        
        return teacher_notes, differentiation_tips

    def prepare_content_for_handler(self, structured_content: List[Dict[str, Any]], resource_type: str = "PRESENTATION") -> List[Dict[str, Any]]:
        """Prepare structured content for document handlers by cleaning all text."""
        if not structured_content or not isinstance(structured_content, list):
            return []
        
        cleaned_content = []
        
        for item in structured_content:
            if not isinstance(item, dict):
                continue
                
            cleaned_item = {
                'title': self.clean_markdown_and_formatting(item.get('title', '')),
                'layout': item.get('layout', 'TITLE_AND_CONTENT'),
                'content': self.clean_content_list(item.get('content', []))
            }
            
            # Preserve structured data for new format
            if 'structured_questions' in item:
                cleaned_item['structured_questions'] = item['structured_questions']
            if 'teacher_notes' in item:
                cleaned_item['teacher_notes'] = item['teacher_notes']
            if 'differentiation_tips' in item:
                cleaned_item['differentiation_tips'] = item['differentiation_tips']
            
            # Resource-specific cleaning
            if resource_type.upper() == "QUIZ":
                # For quizzes, handle questions and answers specially
                questions, answers = self.extract_questions_from_content(item.get('content', []))
                cleaned_item['content'] = questions
                if answers:
                    cleaned_item['answers'] = answers
                
            elif resource_type.upper() == "WORKSHEET":
                # For worksheets, preserve question formatting but keep simple structure
                pass  # Content already cleaned above
                
            elif resource_type.upper() == "LESSON_PLAN":
                # For lesson plans, keep simple structure
                pass  # Content already cleaned above
            
            cleaned_content.append(cleaned_item)
        
        logger.info(f"Cleaned {len(cleaned_content)} items for {resource_type}")
        return cleaned_content