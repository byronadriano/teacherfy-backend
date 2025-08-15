# resources/generators/slide_processor.py - Restored template-based presentation generation
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_VERTICAL_ANCHOR
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE_TYPE
import os
import logging
import re
import io
from PIL import Image
from pptx.parts.image import Image as PptxImage
from collections import Counter

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

def _enhance_structured_content_for_presentation(structured_content):
    """Enhance structured content for better PowerPoint presentation processing"""
    
    if not structured_content or not isinstance(structured_content, list):
        return structured_content
    
    enhanced_content = []
    
    for slide_data in structured_content:
        if not isinstance(slide_data, dict):
            continue
            
        enhanced_slide = {
            'title': slide_data.get('title', 'Untitled'),
            'layout': slide_data.get('layout', 'TITLE_AND_CONTENT'),
            'content': []
        }
        
        # Process content intelligently
        raw_content = slide_data.get('content', [])
        
        if isinstance(raw_content, list):
            for item in raw_content:
                if isinstance(item, str):
                    # Clean and filter content
                    cleaned_item = clean_text_for_presentation(item)
                    if cleaned_item and not _is_metadata_content(cleaned_item):
                        enhanced_slide['content'].append(cleaned_item)
        
        # Add metadata as separate fields for processing
        if 'structured_questions' in slide_data:
            enhanced_slide['structured_questions'] = slide_data['structured_questions']
        
        if 'teacher_notes' in slide_data:
            enhanced_slide['teacher_notes'] = slide_data['teacher_notes']
            
        if 'differentiation_tips' in slide_data:
            enhanced_slide['differentiation_tips'] = slide_data['differentiation_tips']
        
        enhanced_content.append(enhanced_slide)
    
    logger.info(f"Enhanced {len(structured_content)} slides for presentation processing")
    return enhanced_content

def _is_metadata_content(content_text):
    """Check if content is metadata that shouldn't appear on slides"""
    
    metadata_indicators = [
        'teacher note:',
        'differentiation tip:',
        'assessment check:',
        'for teachers:',
        'instructor guidance:',
        'teaching strategy:',
        'lesson plan:'
    ]
    
    content_lower = content_text.lower().strip()
    
    return any(content_lower.startswith(indicator) for indicator in metadata_indicators)

def clear_all_placeholder_content(slide):
    """AGGRESSIVELY clear all placeholder content including master slide placeholders."""
    try:
        placeholders_cleared = 0
        shapes_to_remove = []
        
        for shape in slide.shapes:
            try:
                # Skip title shapes
                if shape == slide.shapes.title:
                    continue
                
                # Check if this is a placeholder shape
                if hasattr(shape, 'is_placeholder') and shape.is_placeholder:
                    # Try multiple clearing methods
                    if hasattr(shape, 'text_frame'):
                        # Method 1: Clear the text frame
                        shape.text_frame.clear()
                        
                        # Method 2: Set text to empty
                        if hasattr(shape.text_frame, 'text'):
                            shape.text_frame.text = ""
                        
                        # Method 3: Remove all paragraphs and add empty one
                        try:
                            shape.text_frame._element.clear()
                        except:
                            pass
                        
                        placeholders_cleared += 1
                        logger.debug(f"Aggressively cleared placeholder shape")
                
                # Also check by placeholder format
                elif hasattr(shape, 'placeholder_format'):
                    placeholder_type = getattr(shape.placeholder_format, 'type', None)
                    if placeholder_type in [2, 7, 8, 14]:  # Content placeholders
                        if hasattr(shape, 'text_frame'):
                            shape.text_frame.clear()
                            if hasattr(shape.text_frame, 'text'):
                                shape.text_frame.text = ""
                            placeholders_cleared += 1
                            logger.debug(f"Cleared placeholder by type: {placeholder_type}")
                
                # Last resort: check for "Click to add" text patterns
                elif hasattr(shape, 'text_frame') and hasattr(shape.text_frame, 'text'):
                    text_content = shape.text_frame.text.lower()
                    if any(phrase in text_content for phrase in ['click to add', 'click to edit', 'add text']):
                        shape.text_frame.clear()
                        shape.text_frame.text = ""
                        placeholders_cleared += 1
                        logger.debug(f"Cleared shape with placeholder text: {text_content[:20]}")
                        
            except Exception as e:
                logger.debug(f"Could not process shape: {e}")
                continue
        
        logger.info(f"Aggressively cleared {placeholders_cleared} placeholder shapes")
        return placeholders_cleared > 0
        
    except Exception as e:
        logger.warning(f"Error in aggressive placeholder clearing: {e}")
        return False

def add_text_box_to_slide(slide, content_items, with_image=False):
    """Add a text box to widescreen slide (13.33" x 7.5") with proper sizing."""
    
    # WIDESCREEN dimensions
    slide_width = Inches(13.33)
    
    if with_image:
        # Text takes up left portion of widescreen, leaving right for image
        left = Inches(0.8)      # Left margin
        top = Inches(2.1)       # Below title
        width = Inches(7.5)     # Much wider for widescreen (about 60% of slide)
        height = Inches(4.2)    # Good height for content
    else:
        # Use most of widescreen when no image
        left = Inches(0.8)
        top = Inches(2.1)
        width = Inches(11.5)    # Much wider for widescreen (about 85% of slide)
        height = Inches(4.5)
    
    # Create text box with widescreen-appropriate dimensions
    textbox = slide.shapes.add_textbox(left, top, width, height)
    text_frame = textbox.text_frame
    text_frame.clear()
    
    # Optimize text frame properties for widescreen
    text_frame.margin_left = Inches(0.2)
    text_frame.margin_right = Inches(0.3)
    text_frame.margin_top = Inches(0.15)
    text_frame.margin_bottom = Inches(0.15)
    text_frame.word_wrap = True
    text_frame.auto_size = None  # Prevent auto-sizing
    
    # Use cleaned content with larger text for widescreen visibility
    cleaned_items = clean_content_list_for_presentation(content_items)
    
    for item in cleaned_items:
        p = text_frame.add_paragraph()
        p.text = f"• {item}"
        p.font.name = STYLE['fonts']['body']
        p.font.size = Pt(20)              # Larger font for widescreen
        p.font.color.rgb = STYLE['colors']['body']
        p.space_after = Pt(8)             # More spacing for readability
        p.line_spacing = 1.2              # Good line spacing
        p.level = 0                       # Consistent bullet level
    
    layout_desc = 'with image accommodation' if with_image else 'full widescreen'
    logger.info(f"Added widescreen text box ({layout_desc}) - size: {width}x{height}")

def create_clean_presentation_with_images(structured_content, include_images=False):
    """Create a PowerPoint presentation from clean structured content with enhanced images"""
    
    # Enhanced content processing for JSON structured data
    processed_content = _enhance_structured_content_for_presentation(structured_content)
    
    # Find template path - updated for new structure
    template_path = os.path.join('static', 'templates', 'FINAL_base_template_v1.pptx')
    
    # Check if template exists, use fallback paths
    if not os.path.exists(template_path):
        fallback_paths = [
            'templates/FINAL_base_template_v1.pptx',
            'static/templates/base_template.pptx',
            'templates/base_template.pptx',
            'src/templates/FINAL_base_template_v1.pptx'  # Old structure fallback
        ]
        for path in fallback_paths:
            if os.path.exists(path):
                template_path = path
                break
    
    # Create presentation
    try:
        prs = Presentation(template_path)
        logger.info(f"✅ Using template: {template_path}")
    except Exception as e:
        logger.warning(f"⚠️ Could not load template: {e}. Creating blank presentation.")
        prs = Presentation()
    
    # Initialize Unsplash service if images are requested
    unsplash_service = None
    
    if include_images:
        try:
            from core.services.unsplash_service import unsplash_service as us
            unsplash_service = us
            logger.info("📸 Unsplash service initialized for per-slide image generation")
        except Exception as e:
            logger.error(f"❌ Error initializing Unsplash service: {e}")
            include_images = False  # Disable images for this generation
    
    # Log available slide layouts for debugging
    logger.info(f"📋 Available slide layouts: {len(prs.slide_layouts)}")
    for i, layout in enumerate(prs.slide_layouts):
        try:
            layout_name = layout.name if hasattr(layout, 'name') else f"Layout {i}"
            logger.debug(f"Layout {i}: {layout_name} - {len(layout.placeholders)} placeholders")
        except:
            logger.debug(f"Layout {i}: Unknown layout")
    
    # Process each slide with clean structure and improved layout
    for slide_index, slide_data in enumerate(processed_content):
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
            
            # Add contextually relevant image to each content slide
            has_image = False
            if include_images and unsplash_service and slide_index > 0:  # Skip learning objectives slide
                try:
                    # Create search query from slide title and content
                    slide_title = slide_data.get('title', '')
                    slide_content = slide_data.get('content', [])
                    
                    # Generate search keywords from this specific slide
                    search_keywords = []
                    if slide_title and slide_title != 'Learning Objectives':
                        search_keywords.append(slide_title.lower())
                    
                    # Extract key terms from slide content
                    content_text = ' '.join(slide_content).lower()
                    for content_item in slide_content[:2]:  # Use first 2 content items
                        words = content_item.lower().split()
                        # Extract meaningful words (nouns, specific terms)
                        meaningful_words = [w for w in words if len(w) > 4 and w not in ['students', 'will', 'able', 'example', 'today']]
                        search_keywords.extend(meaningful_words[:2])
                    
                    # Create focused search query
                    search_query = ' '.join(search_keywords[:3])  # Use top 3 keywords
                    
                    if search_query.strip():
                        logger.info(f"Searching for image for slide {slide_index + 1} with query: '{search_query}'")
                        
                        # Search for slide-specific image
                        image_url = unsplash_service.get_relevant_image(search_query)
                        if image_url:
                            # Add image to slide
                            _add_image_to_slide(slide, image_url)
                            has_image = True
                            logger.info(f"📸 Added image to slide {slide_index + 1}")
                        else:
                            logger.warning(f"⚠️ No image found for slide {slide_index + 1}")
                            
                except Exception as e:
                    logger.error(f"❌ Error adding image to slide {slide_index + 1}: {e}")
                    has_image = False
            
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
            
            # WIDESCREEN CONTENT HANDLING - Fixed for 13.33" x 7.5" template
            raw_content_items = slide_data.get('content', [])
            clean_content_items = clean_content_list_for_presentation(raw_content_items)
            
            if clean_content_items:
                # ALWAYS clear placeholders and use text boxes for consistency
                logger.info(f"Using text box for slide {slide_index + 1} (image: {has_image})")
                
                # CRITICAL: Clear ALL placeholders to prevent conflicts
                clear_all_placeholder_content(slide)
                
                # Add our custom text box with widescreen sizing
                add_text_box_to_slide(slide, clean_content_items, has_image)
                
                # Handle title if needed
                if not title_added and clean_title:
                    # Position title for widescreen
                    title_box = slide.shapes.add_textbox(Inches(1.5), Inches(0.5), Inches(10), Inches(1))
                    title_frame = title_box.text_frame
                    title_para = title_frame.add_paragraph()
                    title_para.text = clean_title
                    title_para.font.name = STYLE['fonts']['title']
                    title_para.font.size = STYLE['sizes']['title']
                    title_para.font.color.rgb = STYLE['colors']['title']
                    title_para.font.bold = True
                    title_para.alignment = PP_ALIGN.CENTER
                    logger.debug(f"Added widescreen title as text box to slide {slide_index + 1}")
        
        except Exception as e:
            logger.error(f"Error creating slide {slide_index + 1}: {e}")
            continue
    
    logger.info(f"🎉 Created presentation with {len(processed_content)} slides (images: {'enabled' if include_images else 'disabled'})")
    return prs

def create_clean_presentation(structured_content):
    """Create a PowerPoint presentation from clean structured content without images"""
    return create_clean_presentation_with_images(structured_content, include_images=False)

def _add_image_to_slide(slide, image_url):
    """Add an image from URL to a slide"""
    try:
        import requests
        from io import BytesIO
        
        # Download image
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        
        # Create image stream
        image_stream = BytesIO(response.content)
        
        # Add image to slide (positioned on right side)
        left = Inches(7.5)  # Right side of slide
        top = Inches(2)     # Below title
        width = Inches(4.5) # Reasonable width
        height = Inches(3.5) # Reasonable height
        
        slide.shapes.add_picture(image_stream, left, top, width, height)
        
    except Exception as e:
        logger.error(f"❌ Error adding image to slide: {e}")
        raise

def parse_outline_to_structured_content(outline_text, resource_type="PRESENTATION"):
    """Parse outline text into clean structured content"""
    logger.info(f"📋 Parsing outline for resource type: {resource_type}")
    
    # More flexible pattern to handle both "Slide X:" and "Section X:" formats
    section_pattern = r"(?:Slide|Section)\s+(\d+):\s*(.*)"
    
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
            logger.debug(f"Found section {section_num}: {section_title}")
        elif line.lower() in ['content', 'content:']:
            # Skip standalone content headers
            continue
        elif line.startswith('-') or line.startswith('•'):
            # This is bulleted content
            if current_section:
                clean_content = clean_text_for_presentation(line.lstrip('-•').strip())
                if clean_content:
                    current_section["content"].append(clean_content)
                    logger.debug(f"Added bulleted content: {clean_content[:40]}...")
        else:
            # Regular content line (after filtering out headers)
            if current_section:
                clean_content = clean_text_for_presentation(line)
                # Skip empty content and standalone headers
                if clean_content and clean_content.lower() not in ['content', 'content:', '---', 'key vocabulary:', 'vocabulary:']:
                    current_section["content"].append(clean_content)
                    logger.debug(f"Added content: {clean_content[:40]}...")
    
    # Add the last section
    if current_section:
        sections.append(current_section)
    
    logger.info(f"✅ Parsed {len(sections)} sections from outline")
    
    # Debug: Show what was parsed
    for i, section in enumerate(sections):
        logger.debug(f"Section {i+1}: '{section.get('title')}' - {len(section.get('content', []))} items")
        for content_item in section.get('content', [])[:2]:  # Show first 2
            logger.debug(f"  Content: {content_item[:50]}...")
    
    return sections