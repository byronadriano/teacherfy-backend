from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_VERTICAL_ANCHOR
from pptx.dml.color import RGBColor
import os
import logging
import re

logger = logging.getLogger(__name__)

# Enhanced presentation styles
STYLE = {
    'colors': {
        'title': RGBColor(44, 62, 80),      # Dark blue-gray for titles
        'body': RGBColor(44, 62, 80),        # Dark blue-gray for body text
        'accent': RGBColor(41, 128, 185)     # Bright blue for emphasis
    },
    'fonts': {
        'title': 'Calibri',
        'body': 'Calibri'
    },
    'sizes': {
        'title': Pt(40),           # Larger title
        'body': Pt(18),           # Readable body text
        'bullet': Pt(16),         # Slightly smaller bullet points
        'notes': Pt(14)           # Comfortable notes size
    }
}

def clean_markdown_formatting(text):
    """Remove markdown formatting while preserving the text structure"""
    if not text:
        return ""
    
    # Remove bold markdown indicators
    text = text.replace('**', '')
    
    # Remove any remaining asterisks at the start of lines
    text = text.lstrip('*')
    
    # Clean up any double spaces that might have been created
    text = ' '.join(text.split())
    
    # Handle numbered lists (e.g., "1.", "2.", etc.)
    text = re.sub(r'^\d+\.\s*', '', text)
    
    # Remove bullet points 
    text = re.sub(r'^[-•*]\s*', '', text)
    
    return text.strip()

def parse_outline_to_structured_content(outline_text, resource_type="PRESENTATION"):
    """Improved parsing to correctly handle different resource types and sections"""
    # Normalize resource type to uppercase for consistency
    resource_type = resource_type.upper() if resource_type else "PRESENTATION"
    logger.info(f"Parsing outline for resource type: {resource_type}")
    
    # Special handling for different resource types
    if resource_type == "QUIZ" or "TEST" in resource_type:
        # Use the specialized quiz parser
        return parse_quiz_test_format(outline_text)
    
    # Dictionary of section identifiers for different resource types
    markers = {
        "PRESENTATION": {
            "section_pattern": r"(?:SLIDE|Slide)\s+(\d+):\s*(.*)",
            "content_header": r"(?:CONTENT|Content):",
            "notes_header": r"(?:TEACHER NOTES|Teacher Notes):",
            "visual_header": r"(?:VISUAL ELEMENTS|Visual Elements):",
        },
        "LESSON_PLAN": {
            "section_pattern": r"(?:SECTION|Section)\s+(\d+):\s*(.*)",
            "content_header": r"(?:CONTENT|Content):",
            "procedure_header": r"(?:PROCEDURE|Procedure):",
            "notes_header": r"(?:TEACHER NOTES|Teacher Notes):",
            "duration_header": r"(?:DURATION|Duration):",
        },
        "WORKSHEET": {
            "section_pattern": r"(?:SECTION|Section|PART|Part)\s+(\d+):\s*(.*)",
            "instructions_header": r"(?:INSTRUCTIONS|Instructions|Instrucciones):",
            "content_header": r"(?:CONTENT|QUESTIONS|Content|Questions|Contenido|Preguntas):",
            "notes_header": r"(?:TEACHER NOTES|Teacher Notes|Notas del Maestro):",
        },
        "QUIZ": {
            "section_pattern": r"(?:SECTION|Section|PART|Part|QUESTION|Question)\s+(\d+):\s*(.*)",
            "content_header": r"(?:QUESTIONS|Questions|CONTENT|Content):",
            "answers_header": r"(?:ANSWERS|Answers|ANSWER KEY|Answer Key):",
            "notes_header": r"(?:TEACHER NOTES|Teacher Notes):",
        }
    }
    
    # Get the appropriate markers for this resource type
    # Default to PRESENTATION if resource type not recognized
    resource_markers = markers.get(resource_type, markers["PRESENTATION"])
    
    # Split the outline text into sections based on the appropriate pattern
    sections = []
    
    # Check if outline text starts with a title that's not a section
    first_line = outline_text.strip().split('\n')[0].strip() if outline_text else ""
    title_not_section = first_line and not re.match(resource_markers["section_pattern"], first_line)
    
    # Extract main title
    main_title = first_line if title_not_section else "Generated Resource"
    
    # For worksheets, try to extract sections more precisely
    if resource_type == "WORKSHEET":
        # Look for section headers in the text
        section_matches = re.finditer(r"\*\*Section\s+(\d+):\s*(.*?)\*\*", outline_text)
        section_boundaries = []
        
        for match in section_matches:
            section_num = match.group(1)
            section_title = match.group(2).strip()
            start_pos = match.start()
            
            section_boundaries.append((start_pos, section_num, section_title))
        
        if section_boundaries:
            section_boundaries.sort()  # Sort by position in text
            
            # Process each section
            for i, (start_pos, section_num, section_title) in enumerate(section_boundaries):
                # Determine end position (start of next section or end of text)
                if i < len(section_boundaries) - 1:
                    end_pos = section_boundaries[i+1][0]
                else:
                    end_pos = len(outline_text)
                
                section_text = outline_text[start_pos:end_pos].strip()
                
                # Extract instructions
                instructions = []
                instructions_match = re.search(r"Instructions:(.*?)(?:Content:|$)", section_text, re.DOTALL)
                if instructions_match:
                    instructions_raw = instructions_match.group(1).strip()
                    instructions = [line.strip().strip('- ') for line in instructions_raw.split('\n') if line.strip()]
                
                # Extract content
                content = []
                content_match = re.search(r"Content:(.*?)(?:Teacher Notes:|$)", section_text, re.DOTALL)
                if content_match:
                    content_raw = content_match.group(1).strip()
                    content = [line.strip().strip('- ') for line in content_raw.split('\n') if line.strip()]
                
                # Extract teacher notes
                teacher_notes = []
                notes_match = re.search(r"Teacher Notes:(.*?)(?:$)", section_text, re.DOTALL)
                if notes_match:
                    notes_raw = notes_match.group(1).strip()
                    teacher_notes = [line.strip().strip('- ') for line in notes_raw.split('\n') if line.strip()]
                
                # Create section with all extracted content
                section = {
                    'title': section_title,
                    'layout': "TITLE_AND_CONTENT",
                    'content': content,
                    'instructions': instructions,
                    'teacher_notes': teacher_notes,
                    'visual_elements': [],
                    'left_column': [],
                    'right_column': []
                }
                
                sections.append(section)
    
    # If no sections were found using the specific extractor
    if not sections:
        # Create a single section with the whole content
        section = {
            'title': main_title,
            'layout': "TITLE_AND_CONTENT",
            'content': [line.strip() for line in outline_text.split('\n') if line.strip()],
            'teacher_notes': [],
            'visual_elements': [],
            'left_column': [],
            'right_column': []
        }
        
        # For worksheets, add empty instructions field
        if resource_type == "WORKSHEET":
            section['instructions'] = []
        
        sections.append(section)
    
    logger.info(f"Successfully parsed {len(sections)} {resource_type} sections")
    return sections

def fallback_parsing(outline_text, resource_type):
    """Fallback method for parsing when the standard approach fails"""
    sections = []
    lines = [line.strip() for line in outline_text.strip().split('\n') if line.strip()]
    
    # Look for patterns that might indicate section boundaries
    for i, line in enumerate(lines):
        if i == 0 or (i > 0 and any(pattern in line.lower() for pattern in [
            "slide", "section", "part", "lesson", "worksheet", "quiz"
        ])):
            # This line might be a section title
            title = clean_markdown_formatting(line)
            
            # Create a new section
            section = {
                'title': title,
                'layout': 'TITLE_AND_CONTENT',
                'content': [],
                'teacher_notes': [],
                'visual_elements': [],
                'left_column': [],
                'right_column': []
            }
            
            # Add resource-specific fields
            if resource_type == "LESSON_PLAN":
                section['procedure'] = []
                section['duration'] = ""
            elif resource_type == "WORKSHEET":
                section['instructions'] = []
            elif resource_type == "QUIZ":
                section['answers'] = []
            
            sections.append(section)
        elif sections and line.startswith(('-', '•', '*')):
            # This looks like a content bullet point
            sections[-1]['content'].append(clean_markdown_formatting(line))
    
    # If we still have no sections, create one catch-all section
    if not sections:
        section = {
            'title': "Generated Content",
            'layout': 'TITLE_AND_CONTENT',
            'content': [clean_markdown_formatting(line) for line in lines if line],
            'teacher_notes': [],
            'visual_elements': [],
            'left_column': [],
            'right_column': []
        }
        
        # Add resource-specific fields
        if resource_type == "LESSON_PLAN":
            section['procedure'] = []
            section['duration'] = ""
        elif resource_type == "WORKSHEET":
            section['instructions'] = []
        elif resource_type == "QUIZ":
            section['answers'] = []
        
        sections.append(section)
    
    return sections

def create_presentation(structured_content, resource_type="PRESENTATION"):
    """Create a PowerPoint presentation from structured content"""
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'base_template_finalv4.pptx')
    
    # Check if template exists, use fallback if not
    if not os.path.exists(template_path):
        fallback_paths = [
            'templates/base_template.pptx',
            '../templates/base_template.pptx',
            'src/templates/base_template.pptx',
            'base_template.pptx'
        ]
        for path in fallback_paths:
            if os.path.exists(path):
                template_path = path
                break
    
    # Create presentation
    try:
        prs = Presentation(template_path)
    except Exception as e:
        logger.warning(f"Could not load template: {e}. Creating blank presentation.")
        prs = Presentation()
    
    for slide_data in structured_content:
        layout_idx = 1 if slide_data['layout'] == "TITLE_AND_CONTENT" else 3
        slide = prs.slides.add_slide(prs.slide_layouts[layout_idx])
        
        # Format title
        if slide.shapes.title:
            title_frame = slide.shapes.title.text_frame
            title_frame.clear()
            title_para = title_frame.add_paragraph()
            title_para.text = clean_markdown_formatting(slide_data['title'])
            title_para.font.name = STYLE['fonts']['title']
            title_para.font.size = STYLE['sizes']['title']
            title_para.font.color.rgb = STYLE['colors']['title']
            title_para.font.bold = True
            title_para.alignment = PP_ALIGN.CENTER
        
        if slide_data['layout'] == "TWO_COLUMN":
            shapes = [shape for shape in slide.placeholders]
            if len(shapes) >= 3:
                left = shapes[1]
                right = shapes[2]
                
                # Left column
                text_frame = left.text_frame
                text_frame.clear()
                for item in slide_data['left_column']:
                    p = text_frame.add_paragraph()
                    p.text = clean_markdown_formatting(item)
                    p.font.name = STYLE['fonts']['body']
                    p.font.size = STYLE['sizes']['bullet']
                    p.font.color.rgb = STYLE['colors']['body']
                
                # Right column
                text_frame = right.text_frame
                text_frame.clear()
                for item in slide_data['right_column']:
                    p = text_frame.add_paragraph()
                    p.text = clean_markdown_formatting(item)
                    p.font.name = STYLE['fonts']['body']
                    p.font.size = STYLE['sizes']['bullet']
                    p.font.color.rgb = STYLE['colors']['body']
        else:
            shapes = [shape for shape in slide.placeholders]
            if len(shapes) >= 2:
                content_placeholder = shapes[1]
                text_frame = content_placeholder.text_frame
                text_frame.clear()
                
                for item in slide_data['content']:
                    p = text_frame.add_paragraph()
                    p.text = clean_markdown_formatting(item)
                    p.font.name = STYLE['fonts']['body']
                    p.font.size = STYLE['sizes']['body']
                    p.font.color.rgb = STYLE['colors']['body']
        
        # For presentations, we skip adding notes 
        # but for backward compatibility, we'll check if there are any notes
        if resource_type != "PRESENTATION" and (slide_data.get('teacher_notes') or slide_data.get('visual_elements')):
            notes_slide = slide.notes_slide
            notes_text = notes_slide.notes_text_frame
            notes_text.clear()
            
            if slide_data.get('teacher_notes'):
                notes_text.text = "Teacher Notes:\n"
                for note in slide_data['teacher_notes']:
                    p = notes_text.add_paragraph()
                    p.text = f"• {clean_markdown_formatting(note)}"
                    p.font.size = STYLE['sizes']['notes']
            
            if slide_data.get('visual_elements'):
                if notes_text.text:
                    p = notes_text.add_paragraph()
                    p.text = "\nVisual Elements:"
                else:
                    notes_text.text = "Visual Elements:\n"
                
                for visual in slide_data['visual_elements']:
                    p = notes_text.add_paragraph()
                    p.text = f"• {clean_markdown_formatting(visual)}"
                    p.font.size = STYLE['sizes']['notes']
    
    return prs

def parse_quiz_test_format(outline_text):
    """
    Specialized parser for quiz/test content that properly separates 
    questions from answers
    """
    import re
    
    # First try to find distinct sections
    sections = []
    
    # Look for section headers like "Section X:" 
    section_headers = re.findall(r"(?:Section|SECTION)\s+(\d+):\s*([^\n]+)", outline_text)
    
    if section_headers:
        # We have proper sections, process each one
        for i, (section_num, section_title) in enumerate(section_headers):
            # Find the content between this section header and the next (or the end)
            start_pattern = f"(?:Section|SECTION)\\s+{section_num}:\\s*{re.escape(section_title)}"
            
            # If this is the last section, go to the end, otherwise to the next section
            if i < len(section_headers) - 1:
                next_num, next_title = section_headers[i+1]
                end_pattern = f"(?:Section|SECTION)\\s+{next_num}:\\s*{re.escape(next_title)}"
                section_content = re.search(
                    f"{start_pattern}(.*?){end_pattern}", 
                    outline_text, 
                    re.DOTALL
                )
            else:
                section_content = re.search(
                    f"{start_pattern}(.*?)(?:$|Overall Test Instructions)", 
                    outline_text, 
                    re.DOTALL
                )
            
            if not section_content:
                continue
                
            content_text = section_content.group(1)
            
            # Create section structure
            section = {
                'title': f"Section {section_num}: {section_title.strip()}",
                'layout': 'TITLE_AND_CONTENT',
                'content': [],
                'answers': [],
                'teacher_notes': [],
                'visual_elements': []
            }
            
            # Find the questions (content)
            content_match = re.search(r"Content:\s*(.*?)(?:Answers:|Teacher Notes:|$)", 
                                     content_text, re.DOTALL)
            if content_match:
                # Extract bullet points or numbered items
                items = re.findall(r"[-•*]?\s*(.*?)(?:\n|$)", content_match.group(1))
                section['content'] = [item.strip() for item in items if item.strip()]
            
            # Find the answers 
            answers_match = re.search(r"Answers:\s*(.*?)(?:Teacher Notes:|$)", 
                                     content_text, re.DOTALL)
            if answers_match:
                # Extract bullet points or numbered items
                items = re.findall(r"[-•*]?\s*(.*?)(?:\n|$)", answers_match.group(1))
                section['answers'] = [item.strip() for item in items if item.strip()]
            
            # Find teacher notes
            notes_match = re.search(r"Teacher Notes:\s*(.*?)(?:$)", 
                                   content_text, re.DOTALL)
            if notes_match:
                # Extract bullet points or numbered items
                items = re.findall(r"[-•*]?\s*(.*?)(?:\n|$)", notes_match.group(1))
                section['teacher_notes'] = [item.strip() for item in items if item.strip()]
            
            sections.append(section)
    
    # If no sections were found, create one section with all content
    if not sections:
        # Create a basic section
        section = {
            'title': "Quiz Questions",
            'layout': 'TITLE_AND_CONTENT',
            'content': [],
            'answers': [],
            'teacher_notes': [],
            'visual_elements': []
        }
        
        # Extract all lines as content
        lines = outline_text.strip().split('\n')
        section['content'] = [line.strip() for line in lines if line.strip()]
        
        sections.append(section)
    
    # Look for general instructions and add them as teacher notes to the last section
    instructions_match = re.search(
        r"(?:Overall Test Instructions:|Test Scoring Guide:|Additional Teacher Notes:)(.*?)$", 
        outline_text, 
        re.DOTALL
    )
    
    if instructions_match and sections:
        instructions = instructions_match.group(1).strip()
        for line in instructions.split('\n'):
            line = line.strip()
            if line and not line.startswith('---'):
                line = re.sub(r'^[-•*]\s*', '', line)  # Remove bullet points
                if line:
                    sections[-1]['teacher_notes'].append(line)
    
    return sections