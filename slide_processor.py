from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_VERTICAL_ANCHOR
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
import os
import logging

logger = logging.getLogger(__name__)

# Enhanced presentation constants
STYLE = {
    'colors': {
        'title': RGBColor(44, 62, 80),      # Dark blue-gray for titles
        'subtitle': RGBColor(52, 73, 94),    # Lighter blue-gray for subtitles
        'body': RGBColor(44, 62, 80),        # Dark blue-gray for body text
        'accent': RGBColor(41, 128, 185),    # Bright blue for emphasis
        'background': RGBColor(236, 240, 241) # Light gray background
    },
    'fonts': {
        'title': 'Calibri',
        'body': 'Calibri'
    },
    'sizes': {
        'title': Pt(44),           # Larger, more visible title
        'subtitle': Pt(32),        # Clear subtitle size
        'body': Pt(28),           # Readable body text
        'bullet': Pt(24),         # Slightly smaller bullet points
        'notes': Pt(12)           # Comfortable notes size
    }
}

def format_paragraph(paragraph, style='body', level=0, is_title=False):
    """Apply consistent formatting to a paragraph"""
    if is_title:
        paragraph.alignment = PP_ALIGN.CENTER
        paragraph.font.size = STYLE['sizes']['title']
        paragraph.font.color.rgb = STYLE['colors']['title']
    else:
        paragraph.alignment = PP_ALIGN.LEFT
        paragraph.font.size = STYLE['sizes']['body'] if level == 0 else STYLE['sizes']['bullet']
        paragraph.font.color.rgb = STYLE['colors']['body']
    
    paragraph.font.name = STYLE['fonts']['title' if is_title else 'body']
    paragraph.font.bold = is_title or level == 0
    
    # Add spacing for readability
    paragraph.space_before = Pt(12 if level > 0 else 20)
    paragraph.space_after = Pt(6)

def parse_outline_to_structured_content(outline_text):
    """Parse the outline text into structured slide content"""
    slides = []
    current_slide = None
    current_section = None
    
    lines = outline_text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('Slide '):
            if current_slide:
                slides.append(current_slide)
            
            # Extract title, handling quotes if present
            title = line.split(':', 1)[1].strip().strip('"')
            
            # Determine layout based on content
            layout = "TWO_CONTENT" if any(word in title.lower() for word in 
                ["vs", "comparison", "contrast", "together", "practice"]) else "CONTENT"
            
            current_slide = {
                'title': title,
                'layout': layout,
                'content': [],
                'teacher_notes': [],
                'visual_elements': [],
                'left_column': [],
                'right_column': []
            }
            current_section = None
            
        elif line.lower().startswith(('content:', 'teacher notes:', 'visual elements:')):
            if line.lower().startswith('content:'):
                current_section = 'content'
            elif line.lower().startswith('teacher notes:'):
                current_section = 'teacher_notes'
            elif line.lower().startswith('visual elements:'):
                current_section = 'visual_elements'
                
        elif current_slide and current_section:
            # Handle bullet points and regular text
            if line.startswith(('-', '•', '*')):
                content = line.lstrip('-•* ').strip()
                if current_section == 'content':
                    if current_slide['layout'] == "TWO_CONTENT":
                        if len(current_slide['left_column']) <= len(current_slide['right_column']):
                            current_slide['left_column'].append(content)
                        else:
                            current_slide['right_column'].append(content)
                    else:
                        current_slide['content'].append(content)
                elif current_section == 'teacher_notes':
                    current_slide['teacher_notes'].append(content)
                elif current_section == 'visual_elements':
                    current_slide['visual_elements'].append(content)
            else:
                # Handle non-bullet text
                if current_section == 'content':
                    if current_slide['layout'] == "TWO_CONTENT":
                        if len(current_slide['left_column']) <= len(current_slide['right_column']):
                            current_slide['left_column'].append(line)
                        else:
                            current_slide['right_column'].append(line)
                    else:
                        current_slide['content'].append(line)
                elif current_section == 'teacher_notes':
                    current_slide['teacher_notes'].append(line)
                elif current_section == 'visual_elements':
                    current_slide['visual_elements'].append(line)
    
    # Add the last slide
    if current_slide:
        slides.append(current_slide)
    
    return slides

def create_presentation(outline_json):
    """Create a PowerPoint presentation with enhanced formatting"""
    # Load template
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'base_template.pptx')
    prs = Presentation(template_path)
    
    for slide_data in outline_json:
        # Select appropriate layout
        layout_idx = 3 if slide_data['layout'] == "TWO_CONTENT" else 1
        slide = prs.slides.add_slide(prs.slide_layouts[layout_idx])
        
        # Format title
        if slide.shapes.title:
            title_frame = slide.shapes.title.text_frame
            title_frame.clear()
            title_para = title_frame.add_paragraph()
            title_para.text = slide_data['title']
            format_paragraph(title_para, is_title=True)
            
        # Handle content based on layout
        if slide_data['layout'] == "TWO_CONTENT":
            # Two-column layout
            shapes = [shape for shape in slide.placeholders]
            if len(shapes) >= 3:  # Title + 2 content placeholders
                left_content = shapes[1].text_frame
                right_content = shapes[2].text_frame
                
                # Format left column
                left_content.clear()
                for item in slide_data['left_column']:
                    para = left_content.add_paragraph()
                    para.text = item
                    format_paragraph(para, level=1 if item.startswith(('•', '-', '*')) else 0)
                
                # Format right column
                right_content.clear()
                for item in slide_data['right_column']:
                    para = right_content.add_paragraph()
                    para.text = item
                    format_paragraph(para, level=1 if item.startswith(('•', '-', '*')) else 0)
        else:
            # Single column layout
            if len(slide.placeholders) >= 2:
                content_frame = slide.placeholders[1].text_frame
                content_frame.clear()
                
                for item in slide_data['content']:
                    para = content_frame.add_paragraph()
                    para.text = item.lstrip('-•* ')
                    format_paragraph(para, level=1 if item.startswith(('•', '-', '*')) else 0)
        
        # Add notes with enhanced formatting
        notes_slide = slide.notes_slide
        notes_frame = notes_slide.notes_text_frame
        notes_frame.clear()
        
        if slide_data['teacher_notes']:
            notes_frame.text = "TEACHER NOTES:\n"
            for note in slide_data['teacher_notes']:
                p = notes_frame.add_paragraph()
                p.text = f"• {note}"
                p.font.size = STYLE['sizes']['notes']
        
        if slide_data['visual_elements']:
            p = notes_frame.add_paragraph()
            p.text = "\nVISUAL ELEMENTS:\n"
            for visual in slide_data['visual_elements']:
                p = notes_frame.add_paragraph()
                p.text = f"• {visual}"
                p.font.size = STYLE['sizes']['notes']
    
    return prs