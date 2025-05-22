# src/utils/text_processing.py - New utility file for text cleaning

import re
import logging

logger = logging.getLogger(__name__)

def clean_markdown_and_formatting(text):
    """
    Remove all markdown formatting and clean up text for document generation.
    This function handles various formatting issues that might come from AI responses.
    """
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
    
    # Remove any remaining asterisks that might be standalone
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

def clean_content_list(content_list):
    """Clean a list of content items, removing formatting and empty items."""
    if not content_list or not isinstance(content_list, list):
        return []
    
    cleaned_list = []
    for item in content_list:
        if isinstance(item, str):
            cleaned_item = clean_markdown_and_formatting(item)
            if cleaned_item:  # Only add non-empty items
                cleaned_list.append(cleaned_item)
    
    return cleaned_list

def extract_question_and_options(text):
    """
    Extract questions and multiple choice options from text.
    Returns a tuple of (question, options_list)
    """
    if not text:
        return text, []
    
    # Clean the text first
    cleaned_text = clean_markdown_and_formatting(text)
    
    # Check if this looks like a multiple choice question
    lines = cleaned_text.split('\n')
    question_lines = []
    options = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this line is a multiple choice option (A), B), C), D))
        if re.match(r'^[A-D]\)\s*.+', line):
            options.append(line)
        else:
            question_lines.append(line)
    
    # Reconstruct the question without the options
    question = ' '.join(question_lines).strip()
    
    return question, options

def format_for_document_type(text, document_type="docx"):
    """
    Format text appropriately for different document types.
    """
    if not text:
        return ""
    
    # Clean markdown first
    clean_text = clean_markdown_and_formatting(text)
    
    if document_type.lower() == "pptx":
        # For PowerPoint, keep text concise and clear
        # Break up long sentences if needed
        if len(clean_text) > 100:
            # Try to break at natural points (periods, commas)
            sentences = clean_text.split('. ')
            if len(sentences) > 1:
                return '. '.join(sentences[:2]) + '.' if not sentences[0].endswith('.') else '. '.join(sentences[:2])
    
    elif document_type.lower() == "docx":
        # For Word documents, preserve full content
        return clean_text
    
    return clean_text

# Integration function for existing handlers
def prepare_content_for_handler(structured_content, resource_type="presentation"):
    """
    Prepare structured content for document handlers by cleaning all text.
    """
    if not structured_content or not isinstance(structured_content, list):
        return []
    
    cleaned_content = []
    
    for item in structured_content:
        if not isinstance(item, dict):
            continue
            
        cleaned_item = {
            'title': clean_markdown_and_formatting(item.get('title', '')),
            'layout': item.get('layout', 'TITLE_AND_CONTENT'),
            'content': clean_content_list(item.get('content', [])),
            'teacher_notes': clean_content_list(item.get('teacher_notes', [])),
            'visual_elements': clean_content_list(item.get('visual_elements', [])),
            'left_column': clean_content_list(item.get('left_column', [])),
            'right_column': clean_content_list(item.get('right_column', []))
        }
        
        # Resource-specific cleaning
        if resource_type.upper() == "QUIZ":
            # For quizzes, handle questions and answers specially
            cleaned_questions = []
            cleaned_answers = []
            
            for content_item in item.get('content', []):
                question, options = extract_question_and_options(content_item)
                if question:
                    cleaned_questions.append(question)
                    if options:
                        cleaned_questions.extend(options)
            
            cleaned_item['content'] = cleaned_questions
            cleaned_item['answers'] = clean_content_list(item.get('answers', []))
            
        elif resource_type.upper() == "WORKSHEET":
            # For worksheets, preserve question formatting
            cleaned_item['instructions'] = clean_content_list(item.get('instructions', []))
            
        elif resource_type.upper() == "LESSON_PLAN":
            # For lesson plans, add additional fields
            cleaned_item['procedure'] = clean_content_list(item.get('procedure', []))
            cleaned_item['duration'] = clean_markdown_and_formatting(item.get('duration', ''))
        
        cleaned_content.append(cleaned_item)
    
    logger.info(f"Cleaned {len(cleaned_content)} items for {resource_type}")
    return cleaned_content