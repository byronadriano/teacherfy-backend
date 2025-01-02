from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

class SlideLayouts:
    TITLE_SLIDE = 0  # First slide
    TITLE_CONTENT = 1  # Standard layout
    TITLE_TWO_CONTENT = 3  # Two column layout
    TITLE_ONLY = 5  # Title only for special slides

def parse_outline_to_json(outline_text):
    """Convert the outline text into a structured JSON format"""
    slides = []
    current_slide = None
    lines = outline_text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if 'Slide' in line and ':' in line:
            if current_slide:
                slides.append(current_slide)
            
            # Extract slide number and title
            slide_parts = line.split(':', 1)
            title = slide_parts[1].strip() if len(slide_parts) > 1 else line
            
            # Determine layout based on content
            layout_type = "TITLE_CONTENT"
            if "vs." in title.lower() or "comparison" in title.lower():
                layout_type = "TWO_COLUMN"
            elif any(word in title.lower() for word in ["introduction", "summary", "conclusion"]):
                layout_type = "TITLE_ONLY"
            
            current_slide = {
                'title': title,
                'layout': layout_type,
                'main_content': [],
                'left_column': [],
                'right_column': [],
                'bullets': []
            }
        elif line.startswith(('*', '-', '•')):
            if current_slide:
                bullet = line.lstrip('*- •').strip()
                if current_slide['layout'] == "TWO_COLUMN":
                    if len(current_slide['left_column']) <= len(current_slide['right_column']):
                        current_slide['left_column'].append(bullet)
                    else:
                        current_slide['right_column'].append(bullet)
                else:
                    current_slide['bullets'].append(bullet)
        elif current_slide:
            current_slide['main_content'].append(line)
    
    if current_slide:
        slides.append(current_slide)
    
    return slides

def create_presentation(slides_data):
    """Create a PowerPoint presentation from structured slide data"""
    prs = Presentation()
    
    for slide_data in slides_data:
        layout_type = slide_data['layout']
        
        if layout_type == "TWO_COLUMN":
            slide = create_two_column_slide(prs, slide_data)
        elif layout_type == "TITLE_ONLY":
            slide = create_title_only_slide(prs, slide_data)
        else:
            slide = create_standard_slide(prs, slide_data)
        
        apply_slide_styling(slide)
    
    return prs

def create_standard_slide(prs, slide_data):
    """Create a standard title and content slide"""
    slide = prs.slides.add_slide(prs.slide_layouts[SlideLayouts.TITLE_CONTENT])
    
    # Add title
    title = slide.shapes.title
    title.text = slide_data['title']
    
    # Add content
    content = slide.placeholders[1]
    tf = content.text_frame
    
    # Add main content if any
    if slide_data['main_content']:
        p = tf.add_paragraph()
        p.text = '\n'.join(slide_data['main_content'])
    
    # Add bullets
    for bullet in slide_data['bullets']:
        p = tf.add_paragraph()
        p.text = bullet
        p.level = 1
    
    return slide

def create_two_column_slide(prs, slide_data):
    """Create a slide with two columns"""
    slide = prs.slides.add_slide(prs.slide_layouts[SlideLayouts.TITLE_TWO_CONTENT])
    
    # Add title
    title = slide.shapes.title
    title.text = slide_data['title']
    
    # Left column
    left = slide.placeholders[1]
    tf_left = left.text_frame
    for bullet in slide_data['left_column']:
        p = tf_left.add_paragraph()
        p.text = bullet
        p.level = 1
    
    # Right column
    right = slide.placeholders[2]
    tf_right = right.text_frame
    for bullet in slide_data['right_column']:
        p = tf_right.add_paragraph()
        p.text = bullet
        p.level = 1
    
    return slide

def create_title_only_slide(prs, slide_data):
    """Create a title-focused slide with centered content"""
    slide = prs.slides.add_slide(prs.slide_layouts[SlideLayouts.TITLE_ONLY])
    
    # Add title
    title = slide.shapes.title
    title.text = slide_data['title']
    
    # Add content in a text box
    left = Inches(1)
    top = Inches(2.5)
    width = Inches(8)
    height = Inches(4)
    
    textbox = slide.shapes.add_textbox(left, top, width, height)
    tf = textbox.text_frame
    tf.word_wrap = True
    
    # Add main content and bullets
    for content in slide_data['main_content']:
        p = tf.add_paragraph()
        p.text = content
        p.alignment = PP_ALIGN.CENTER
    
    for bullet in slide_data['bullets']:
        p = tf.add_paragraph()
        p.text = bullet
        p.alignment = PP_ALIGN.CENTER
    
    return slide

def apply_slide_styling(slide):
    """Apply consistent styling to a slide"""
    # Style the title
    if slide.shapes.title:
        title_format = slide.shapes.title.text_frame.paragraphs[0].font
        title_format.size = Pt(32)
        title_format.name = 'Calibri'
        title_format.bold = True
    
    # Style all text frames
    for shape in slide.shapes:
        if hasattr(shape, "text_frame"):
            for paragraph in shape.text_frame.paragraphs:
                font = paragraph.font
                font.size = Pt(18)
                font.name = 'Calibri'
                if paragraph.level == 1:  # Bullet points
                    font.size = Pt(16)