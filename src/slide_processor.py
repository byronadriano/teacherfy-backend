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
    """Parse the outline text into structured content based on resource type."""
    # Normalize resource type to uppercase for consistency
    resource_type = resource_type.upper() if resource_type else "PRESENTATION"
    logger.info(f"Parsing outline for resource type: {resource_type}")
    
    # Define identification patterns for different resource types
    markers = {
        "PRESENTATION": {
            "section_pattern": r"(?:SLIDE|Slide)\s+(\d+):\s*(.*)",
            "content_header": r"(?:CONTENT|Content):",
            # Note: For presentations, we no longer expect these sections:
            # "notes_header": r"(?:TEACHER NOTES|Teacher Notes):",
            # "visual_header": r"(?:VISUAL ELEMENTS|Visual Elements):",
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
            "content_header": r"(?:CONTENT|Content|QUESTIONS|Questions):",
            "instructions_header": r"(?:INSTRUCTIONS|Instructions):",
            "notes_header": r"(?:TEACHER NOTES|Teacher Notes):",
        },
        "QUIZ": {
            "section_pattern": r"(?:SECTION|Section|PART|Part)\s+(\d+):\s*(.*)",
            "content_header": r"(?:QUESTIONS|Questions|CONTENT|Content):",
            "notes_header": r"(?:TEACHER NOTES|Teacher Notes):",
            "answers_header": r"(?:ANSWERS|Answers):",
        }
    }
    
    # Get the appropriate markers for this resource type
    # Default to PRESENTATION if resource type not recognized
    resource_markers = markers.get(resource_type, markers["PRESENTATION"])
    
    # Split into lines and clean up
    lines = [line.strip() for line in outline_text.strip().split('\n') if line.strip()]
    
    # Initialize variables
    sections = []
    current_section = None
    current_part = None
    
    # Process each line
    for line in lines:
        try:
            # Check if this line starts a new section (slide, lesson part, etc.)
            section_match = re.match(resource_markers["section_pattern"], line, re.IGNORECASE)
            
            if section_match:
                # If we have a current section, add it to our list before starting a new one
                if current_section:
                    sections.append(current_section)
                
                # Extract section number and title
                section_num = section_match.group(1)
                section_title = section_match.group(2).strip()
                
                # Create a new section with standard fields for all resource types
                current_section = {
                    'title': section_title,
                    'layout': "TITLE_AND_CONTENT",
                    'content': [],
                    'teacher_notes': [],  # We'll still keep this field for compatibility but it may remain empty for presentations
                    'visual_elements': [], # We'll still keep this field for compatibility but it may remain empty for presentations
                    'left_column': [],
                    'right_column': []
                }
                
                # Add resource-specific fields
                if resource_type == "LESSON_PLAN":
                    current_section['procedure'] = []
                    current_section['duration'] = ""
                elif resource_type == "WORKSHEET":
                    current_section['instructions'] = []
                elif resource_type == "QUIZ":
                    current_section['answers'] = []
                
                current_part = None
                continue
            
            # Skip if we haven't found a section yet
            if not current_section:
                continue
            
            # Check for section headers
            for header_name, pattern in resource_markers.items():
                if header_name.endswith("_header") and re.match(pattern, line, re.IGNORECASE):
                    # Found a section header - update the current part
                    current_part = header_name.replace("_header", "")
                    break
            
            # If this line is a header, skip to the next line
            is_header = False
            for header_name, pattern in resource_markers.items():
                if header_name.endswith("_header") and re.match(pattern, line, re.IGNORECASE):
                    is_header = True
                    break
            if is_header:
                continue
            
            # Process content based on the current part
            if current_part:
                # Skip if the line is empty
                if not line:
                    continue
                    
                # Clean the line (remove bullet points, etc.)
                cleaned_line = line.lstrip('•-* ').strip()
                if not cleaned_line:
                    continue
                
                # Add to the appropriate section based on current part
                if current_part == "content":
                    current_section['content'].append(cleaned_line)
                elif current_part == "notes" and resource_type != "PRESENTATION":
                    # Only add to teacher_notes if not a presentation
                    current_section['teacher_notes'].append(cleaned_line)
                elif current_part == "visual" and resource_type != "PRESENTATION":
                    # Only add to visual_elements if not a presentation
                    current_section['visual_elements'].append(cleaned_line)
                elif current_part == "procedure" and resource_type == "LESSON_PLAN":
                    current_section['procedure'].append(cleaned_line)
                elif current_part == "instructions" and resource_type == "WORKSHEET":
                    current_section['instructions'].append(cleaned_line)
                elif current_part == "answers" and resource_type == "QUIZ":
                    current_section['answers'].append(cleaned_line)
                elif current_part == "duration" and resource_type == "LESSON_PLAN":
                    current_section['duration'] = cleaned_line
            
            # If line looks like a bullet point and we don't have a current part, assume it's content
            elif line.startswith(('-', '•', '*')):
                current_section['content'].append(line.lstrip('•-* ').strip())
        
        except Exception as e:
            logger.error(f"Error parsing line '{line}': {str(e)}")
            continue
    
    # Don't forget to add the last section
    if current_section:
        sections.append(current_section)
    
    # If no valid sections were found, try a fallback approach
    if not sections:
        logger.warning(f"No valid {resource_type} sections found in outline. Attempting fallback parsing.")
        sections = fallback_parsing(outline_text, resource_type)
    
    # Validate and clean up sections
    for section in sections:
        # Clean title
        section['title'] = clean_markdown_formatting(section['title'])
        
        # Ensure we have content for each section
        if not section['content'] and not (section['left_column'] or section['right_column']):
            section['content'] = ["Content placeholder"]
        
        # For two-column layout, split content if needed
        if "two" in section.get('layout', '').lower() and section['content'] and not (section['left_column'] or section['right_column']):
            content_length = len(section['content'])
            mid_point = content_length // 2
            section['left_column'] = section['content'][:mid_point]
            section['right_column'] = section['content'][mid_point:]
            section['content'] = []
    
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