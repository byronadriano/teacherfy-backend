from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

def parse_outline_to_structured_content(outline_text):
    """Parse the outline text into structured slide content with notes"""
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
            
            # Extract slide number and title
            title = line.split(':', 1)[1].strip() if ':' in line else line
            
            # Determine layout based on content
            layout = "TWO_COLUMN" if any(word in title.lower() for word in 
                ["vs", "comparison", "contrast"]) else "TITLE_CONTENT"
            
            current_slide = {
                'title': title,
                'layout': layout,
                'content': [],
                'teacher_notes': [],
                'visual_elements': [],
                'left_column': [],
                'right_column': []
            }
            current_section = 'content'
            
        elif line.lower().startswith('teacher note'):
            current_section = 'teacher_notes'
        elif line.lower().startswith('visual'):
            current_section = 'visual_elements'
        elif line.lower().startswith('content'):
            current_section = 'content'
        elif line.startswith(('-', '*', '•')):
            content = line.lstrip('-*• ').strip()
            if current_slide:
                if current_slide['layout'] == "TWO_COLUMN" and current_section == 'content':
                    if len(current_slide['left_column']) <= len(current_slide['right_column']):
                        current_slide['left_column'].append(content)
                    else:
                        current_slide['right_column'].append(content)
                else:
                    current_slide[current_section].append(content)
        else:
            if current_slide and not line.lower().endswith(':'):
                current_slide[current_section].append(line)
    
    if current_slide:
        slides.append(current_slide)
    
    return slides

def create_presentation(outline_json):
    """Create a PowerPoint presentation with notes from structured content"""
    prs = Presentation()
    
    for slide_data in outline_json:
        # Choose layout
        if slide_data['layout'] == "TWO_COLUMN":
            slide = prs.slides.add_slide(prs.slide_layouts[3])  # Two content layout
        else:
            slide = prs.slides.add_slide(prs.slide_layouts[1])  # Title and content layout
        
        # Add title
        title = slide.shapes.title
        title.text = slide_data['title']
        
        if slide_data['layout'] == "TWO_COLUMN":
            # Add two columns
            left = slide.placeholders[1]
            right = slide.placeholders[2]
            
            add_content_with_formatting(left.text_frame, slide_data['left_column'])
            add_content_with_formatting(right.text_frame, slide_data['right_column'])
        else:
            # Add main content
            content = slide.placeholders[1]
            add_content_with_formatting(content.text_frame, slide_data['content'])
        
        # Add notes
        notes_slide = slide.notes_slide
        notes_text = notes_slide.notes_text_frame
        
        if slide_data['teacher_notes']:
            notes_text.text = "TEACHER NOTES:\n" + "\n".join(
                f"• {note}" for note in slide_data['teacher_notes']
            )
        
        if slide_data['visual_elements']:
            if notes_text.text:
                notes_text.text += "\n\nVISUAL ELEMENTS:\n"
            else:
                notes_text.text = "VISUAL ELEMENTS:\n"
            notes_text.text += "\n".join(
                f"• {visual}" for visual in slide_data['visual_elements']
            )
    
    return prs

def add_content_with_formatting(text_frame, content):
    """Add content to a text frame with consistent formatting"""
    text_frame.clear()
    
    for item in content:
        p = text_frame.add_paragraph()
        p.text = item
        p.font.size = Pt(18)
        p.font.name = 'Calibri'
        
        # Add bullet points for items that look like bullet points
        if item.startswith(('•', '-', '*')):
            p.level = 1
            p.font.size = Pt(16)  # Slightly smaller for bullet points