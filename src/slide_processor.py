# src/slide_processor.py - Updated with better text cleaning
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_VERTICAL_ANCHOR
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE_TYPE
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

def clean_text_for_presentation(text):
    """
    Clean text specifically for PowerPoint presentations.
    Remove all markdown and formatting while preserving readability.
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
    
    # Remove section dividers and markers
    text = re.sub(r'^---+$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\*\*Section \d+:', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\*\*Slide \d+:', '', text, flags=re.MULTILINE)
    
    # Clean up standalone asterisks
    text = re.sub(r'^\*+\s*', '', text)             # Remove leading asterisks
    text = re.sub(r'\s*\*+$', '', text)             # Remove trailing asterisks
    
    # Clean up bullet points and numbering (but preserve the content)
    text = re.sub(r'^[-•*]\s*', '', text)           # Remove bullet points
    text = re.sub(r'^\d+\.\s*', '', text)           # Remove numbering
    
    # Clean up multiple spaces and normalize whitespace
    text = ' '.join(text.split())
    
    # Remove any remaining special formatting characters
    text = text.replace('---', '')                   # Remove horizontal rules
    text = text.replace('***', '')                   # Remove emphasis combinations
    
    # Remove content labels that might have been included
    if text.lower().startswith('content:'):
        text = text[8:].strip()
    
    return text.strip()

def clean_content_list_for_presentation(content_list):
    """Clean a list of content items for presentation use."""
    if not content_list or not isinstance(content_list, list):
        return []
    
    cleaned_list = []
    for item in content_list:
        if isinstance(item, str):
            cleaned_item = clean_text_for_presentation(item)
            # Skip empty items and content headers
            if cleaned_item and cleaned_item.lower() not in ['content', 'content:', '---']:
                cleaned_list.append(cleaned_item)
    
    return cleaned_list

def find_content_placeholder(slide):
    """Find a suitable content placeholder on the slide"""
    # Try to find placeholders in order of preference
    for placeholder in slide.placeholders:
        try:
            # Check if it's a content placeholder (not title)
            if hasattr(placeholder, 'placeholder_format') and placeholder.placeholder_format.type:
                placeholder_type = placeholder.placeholder_format.type
                # Look for content, body, or object placeholders
                if placeholder_type in [2, 7, 8, 14]:  # CONTENT, BODY, OBJECT, CONTENT_WITH_CAPTION
                    return placeholder
        except:
            continue
    
    # If no specific content placeholder found, try by index
    try:
        # Most templates have content at index 1
        if len(slide.placeholders) > 1:
            return slide.placeholders[1]
    except:
        pass
    
    # Last resort: find any text-capable placeholder that's not the title
    for i, placeholder in enumerate(slide.placeholders):
        try:
            if i == 0:  # Skip title placeholder
                continue
            # Test if we can access text_frame
            if hasattr(placeholder, 'text_frame'):
                return placeholder
        except:
            continue
    
    return None

def add_text_box_to_slide(slide, content_items):
    """Add a text box to the slide if no placeholder is available"""
    # Create a text box
    left = Inches(1)
    top = Inches(2)
    width = Inches(8)
    height = Inches(5)
    
    textbox = slide.shapes.add_textbox(left, top, width, height)
    text_frame = textbox.text_frame
    text_frame.clear()
    
    # Use cleaned content
    cleaned_items = clean_content_list_for_presentation(content_items)
    
    for item in cleaned_items:
        p = text_frame.add_paragraph()
        p.text = f"• {item}"
        p.font.name = STYLE['fonts']['body']
        p.font.size = STYLE['sizes']['body']
        p.font.color.rgb = STYLE['colors']['body']
    
    logger.info("Added text box to slide due to missing placeholders")

def create_clean_presentation(structured_content):
    """Create a PowerPoint presentation from clean structured content"""
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
        logger.info(f"Using template: {template_path}")
    except Exception as e:
        logger.warning(f"Could not load template: {e}. Creating blank presentation.")
        prs = Presentation()
    
    # Log available slide layouts for debugging
    logger.info(f"Available slide layouts: {len(prs.slide_layouts)}")
    for i, layout in enumerate(prs.slide_layouts):
        try:
            layout_name = layout.name if hasattr(layout, 'name') else f"Layout {i}"
            logger.debug(f"Layout {i}: {layout_name} - {len(layout.placeholders)} placeholders")
        except:
            logger.debug(f"Layout {i}: Unknown layout")
    
    # Process each slide with clean structure
    for slide_index, slide_data in enumerate(structured_content):
        try:
            # Try different layouts in order of preference
            layout_indices_to_try = [1, 0, 2, 3, 4]  # Title+Content, Title, Section, etc.
            slide = None
            
            for layout_idx in layout_indices_to_try:
                if layout_idx < len(prs.slide_layouts):
                    try:
                        slide = prs.slides.add_slide(prs.slide_layouts[layout_idx])
                        logger.debug(f"Successfully used layout {layout_idx} for slide {slide_index + 1}")
                        break
                    except Exception as e:
                        logger.debug(f"Failed to use layout {layout_idx}: {e}")
                        continue
            
            if not slide:
                # Fallback to the first available layout
                slide = prs.slides.add_slide(prs.slide_layouts[0])
                logger.warning(f"Using fallback layout 0 for slide {slide_index + 1}")
            
            # Clean and add title
            title_added = False
            raw_title = slide_data.get('title', 'Untitled')
            clean_title = clean_text_for_presentation(raw_title)
            
            if slide.shapes.title:
                try:
                    title_frame = slide.shapes.title.text_frame
                    title_frame.clear()
                    title_para = title_frame.add_paragraph()
                    title_para.text = clean_title
                    title_para.font.name = STYLE['fonts']['title']
                    title_para.font.size = STYLE['sizes']['title']
                    title_para.font.color.rgb = STYLE['colors']['title']
                    title_para.font.bold = True
                    title_para.alignment = PP_ALIGN.CENTER
                    title_added = True
                    logger.debug(f"Added clean title to slide {slide_index + 1}: {clean_title}")
                except Exception as e:
                    logger.warning(f"Failed to add title to slide {slide_index + 1}: {e}")
            
            # Clean and add content
            raw_content_items = slide_data.get('content', [])
            clean_content_items = clean_content_list_for_presentation(raw_content_items)
            
            if clean_content_items:
                content_placeholder = find_content_placeholder(slide)
                
                if content_placeholder:
                    try:
                        text_frame = content_placeholder.text_frame
                        text_frame.clear()
                        
                        for item in clean_content_items:
                            p = text_frame.add_paragraph()
                            p.text = item
                            p.font.name = STYLE['fonts']['body']
                            p.font.size = STYLE['sizes']['body']
                            p.font.color.rgb = STYLE['colors']['body']
                            p.level = 0  # Main bullet level
                        
                        logger.debug(f"Added {len(clean_content_items)} clean content items to slide {slide_index + 1}")
                    except Exception as e:
                        logger.warning(f"Failed to add content to placeholder on slide {slide_index + 1}: {e}")
                        # Fallback to text box
                        add_text_box_to_slide(slide, clean_content_items)
                else:
                    # No suitable placeholder found, create a text box
                    logger.warning(f"No content placeholder found on slide {slide_index + 1}, using text box")
                    add_text_box_to_slide(slide, clean_content_items)
                    
                    # If we couldn't add a title through placeholder, add it as text box too
                    if not title_added and clean_title:
                        title_box = slide.shapes.add_textbox(Inches(1), Inches(0.5), Inches(8), Inches(1))
                        title_frame = title_box.text_frame
                        title_para = title_frame.add_paragraph()
                        title_para.text = clean_title
                        title_para.font.name = STYLE['fonts']['title']
                        title_para.font.size = STYLE['sizes']['title']
                        title_para.font.color.rgb = STYLE['colors']['title']
                        title_para.font.bold = True
                        title_para.alignment = PP_ALIGN.CENTER
                        logger.debug(f"Added title as text box to slide {slide_index + 1}")
        
        except Exception as e:
            logger.error(f"Error creating slide {slide_index + 1}: {e}")
            # Create a basic slide with text boxes as last resort
            try:
                slide = prs.slides.add_slide(prs.slide_layouts[0])
                
                # Add title as text box
                clean_title = clean_text_for_presentation(slide_data.get('title', f'Slide {slide_index + 1}'))
                title_box = slide.shapes.add_textbox(Inches(1), Inches(0.5), Inches(8), Inches(1))
                title_frame = title_box.text_frame
                title_para = title_frame.add_paragraph()
                title_para.text = clean_title
                title_para.font.name = STYLE['fonts']['title']
                title_para.font.size = STYLE['sizes']['title']
                title_para.font.color.rgb = STYLE['colors']['title']
                title_para.font.bold = True
                title_para.alignment = PP_ALIGN.CENTER
                
                # Add content as text box
                content_items = slide_data.get('content', [])
                if content_items:
                    add_text_box_to_slide(slide, content_items)
                
                logger.info(f"Created fallback slide {slide_index + 1} with text boxes")
            except Exception as fallback_error:
                logger.error(f"Failed to create fallback slide {slide_index + 1}: {fallback_error}")
    
    logger.info(f"Created presentation with {len(structured_content)} slides")
    return prs

# BACKWARD COMPATIBILITY - Keep the old function for existing code
def create_presentation(structured_content, resource_type="PRESENTATION"):
    """Legacy function for backward compatibility"""
    # Convert old structure to new clean structure if needed
    clean_content = []
    
    for slide_data in structured_content:
        # Clean all the text content
        clean_slide = {
            'title': clean_text_for_presentation(slide_data.get('title', 'Untitled')),
            'layout': slide_data.get('layout', 'TITLE_AND_CONTENT'),
            'content': clean_content_list_for_presentation(slide_data.get('content', []))
        }
        
        # Handle old structure fields - convert to content and clean
        if not clean_slide['content']:
            # Try to extract from old fields
            if slide_data.get('left_column') or slide_data.get('right_column'):
                combined_content = (slide_data.get('left_column', []) + 
                                 slide_data.get('right_column', []))
                clean_slide['content'] = clean_content_list_for_presentation(combined_content)
            elif slide_data.get('teacher_notes'):
                clean_slide['content'] = clean_content_list_for_presentation(slide_data.get('teacher_notes', []))
        
        clean_content.append(clean_slide)
    
    return create_clean_presentation(clean_content)

def parse_outline_to_structured_content(outline_text, resource_type="PRESENTATION"):
    """Parse outline text into clean structured content"""
    logger.info(f"Parsing outline for resource type: {resource_type}")
    
    # Determine section/slide pattern based on resource type
    if resource_type.upper() == "PRESENTATION":
        section_pattern = r"Slide (\d+):\s*(.*)"
        section_word = "Slide"
    else:
        section_pattern = r"Section (\d+):\s*(.*)"
        section_word = "Section"
    
    # Split by section headers
    sections = []
    current_section = None
    
    lines = outline_text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this is a section/slide header
        match = re.match(section_pattern, line)
        if match:
            # Save previous section
            if current_section:
                sections.append(current_section)
            
            # Start new section
            section_num = match.group(1)
            section_title = match.group(2).strip()
            current_section = {
                "title": clean_text_for_presentation(section_title),
                "layout": "TITLE_AND_CONTENT",
                "content": []
            }
        elif line.lower() == "content:":
            # Skip content headers
            continue
        elif line.startswith('-') or line.startswith('•'):
            # This is content
            if current_section:
                clean_content = clean_text_for_presentation(line.lstrip('-•').strip())
                if clean_content:
                    current_section["content"].append(clean_content)
        elif current_section and line:
            # Any other non-empty line goes to content
            clean_content = clean_text_for_presentation(line)
            if clean_content:
                current_section["content"].append(clean_content)
    
    # Don't forget the last section
    if current_section:
        sections.append(current_section)
    
    # If no sections found, create a fallback
    if not sections:
        sections.append({
            "title": "Generated Content",
            "layout": "TITLE_AND_CONTENT",
            "content": [clean_text_for_presentation(line.strip()) for line in lines if line.strip()]
        })
    
    logger.info(f"Successfully parsed {len(sections)} sections for {resource_type}")
    return sections