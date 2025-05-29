# src/slide_processor.py - Enhanced with better image relevance and layout
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

def extract_enhanced_search_keywords(structured_content):
    """
    Extract highly relevant keywords from slide content for better image search.
    Focus on concrete, visual concepts that would make good educational images.
    """
    # Combine all text content from all slides for better context
    all_text = []
    
    for slide in structured_content:
        # Add title
        if slide.get('title'):
            all_text.append(slide['title'])
        
        # Add main content
        if slide.get('content'):
            all_text.extend(slide['content'])
    
    # Join all text
    text = ' '.join(all_text).lower()
    
    # Enhanced subject-specific keyword mapping for better, more relevant image results
    subject_keywords = {
        # Math concepts - more specific and visual
        'fraction': 'fraction circles pizza mathematics classroom visual',
        'fractions': 'fraction pie chart mathematics visual colorful',
        'equivalent': 'equal fractions mathematics visual diagram',
        'equivalent fractions': 'fraction circles equivalent mathematics classroom',
        'place value': 'place value chart hundreds tens ones blocks',
        'powers of 10': 'place value chart mathematics powers ten',
        'addition': 'addition blocks mathematics hands-on colorful',
        'subtraction': 'subtraction mathematics visual blocks counting',
        'multiplication': 'multiplication arrays mathematics grid pattern',
        'division': 'division mathematics sharing groups visual',
        'geometry': 'geometric shapes mathematics classroom poster colorful',
        'measurement': 'ruler measurement mathematics tools classroom',
        'algebra': 'algebra mathematics equation board variables',
        'numbers': 'numbers mathematics classroom poster colorful',
        'counting': 'counting mathematics fingers blocks colorful',
        'patterns': 'pattern blocks mathematics colorful shapes',
        'decimals': 'decimal place value mathematics chart',
        'percentage': 'percentage chart mathematics visual',
        
        # Science concepts - more specific and educational
        'photosynthesis': 'plant photosynthesis diagram science classroom',
        'solar system': 'solar system planets model classroom educational',
        'ecosystem': 'ecosystem food chain science diagram poster',
        'water cycle': 'water cycle evaporation science educational poster',
        'magnetism': 'magnets horseshoe science experiment classroom',
        'electricity': 'electric circuit battery science experiment',
        'weather': 'weather instruments thermometer science classroom',
        'animals': 'animal classification science chart educational',
        'plants': 'plant parts science diagram leaves educational',
        'earth': 'earth science globe classroom model',
        'volcano': 'volcano science model diagram educational',
        'rocks': 'rock minerals science collection classroom',
        'states of matter': 'solid liquid gas science diagram',
        'force': 'force motion science physics experiment',
        
        # Language Arts - more educational focus
        'reading': 'children reading books library classroom engaged',
        'writing': 'student writing pencil paper classroom focused',
        'vocabulary': 'vocabulary words flashcards classroom wall',
        'grammar': 'grammar chart classroom poster educational',
        'poetry': 'poetry books classroom reading circle',
        'story': 'storytelling children books circle time classroom',
        'letters': 'alphabet letters classroom wall colorful',
        'words': 'sight words classroom poster educational',
        'phonics': 'phonics sounds classroom chart letters',
        'comprehension': 'reading comprehension books students engaged',
        'spelling': 'spelling words classroom board letters',
        'literature': 'books literature classroom library reading',
        
        # Social Studies - more educational and visual
        'history': 'history timeline classroom poster educational',
        'geography': 'world map classroom globe colorful',
        'community': 'community helpers people jobs educational',
        'culture': 'cultural diversity classroom multicultural flags',
        'government': 'government classroom civics poster educational',
        'map': 'map geography classroom wall educational',
        'countries': 'world countries map classroom flags',
        'states': 'united states map classroom educational',
        'timeline': 'history timeline classroom poster educational',
        'citizenship': 'citizenship community classroom poster',
        
        # General educational terms with better context
        'learning': 'students learning classroom engaged colorful',
        'classroom': 'elementary classroom colorful educational bright',
        'school': 'school classroom learning environment bright',
        'teacher': 'teacher students classroom interaction engaged',
        'students': 'students classroom learning together collaborative',
        'education': 'education classroom learning materials colorful',
        'lesson': 'classroom lesson teaching materials educational',
        'practice': 'students practice worksheet classroom focused',
        'explore': 'students exploring hands-on learning classroom',
        'discover': 'children discovering learning classroom excited'
    }
    
    # Look for the most specific matches first (longer phrases)
    sorted_keywords = sorted(subject_keywords.items(), key=lambda x: len(x[0]), reverse=True)
    
    for keyword, search_term in sorted_keywords:
        if keyword in text:
            logger.info(f"Found specific keyword '{keyword}', using enhanced search term: '{search_term}'")
            return search_term
    
    # Extract key educational nouns if no specific mapping found
    educational_context = []
    
    # Check for grade level indicators to add appropriate context
    if any(grade in text for grade in ['kindergarten', 'pre-k', 'preschool']):
        educational_context.append('kindergarten')
    elif any(grade in text for grade in ['elementary', '1st', '2nd', '3rd', '4th', '5th']):
        educational_context.append('elementary')
    elif any(grade in text for grade in ['middle', '6th', '7th', '8th']):
        educational_context.append('middle school')
    elif any(grade in text for grade in ['high', '9th', '10th', '11th', '12th']):
        educational_context.append('high school')
    
    # Check for subject indicators with enhanced specificity
    subject_context = []
    if any(subj in text for subj in ['math', 'number', 'calculate', 'equation']):
        subject_context.append('mathematics classroom')
    if any(subj in text for subj in ['science', 'experiment', 'hypothesis', 'observe']):
        subject_context.append('science classroom')
    if any(subj in text for subj in ['reading', 'writing', 'book', 'story', 'letter']):
        subject_context.append('reading classroom')
    if any(subj in text for subj in ['history', 'geography', 'social', 'community']):
        subject_context.append('social studies classroom')
    
    # Extract meaningful content words
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
    
    # Educational priority words that make good visual searches
    priority_words = {
        'learn', 'study', 'practice', 'understand', 'explore', 'discover', 
        'solve', 'create', 'think', 'analyze', 'compare', 'identify',
        'numbers', 'letters', 'words', 'books', 'chart', 'diagram',
        'blocks', 'tools', 'model', 'poster', 'visual', 'hands'
    }
    
    # Common words to avoid in searches
    stop_words = {
        'the', 'and', 'but', 'will', 'can', 'are', 'you', 'for', 'how', 'what', 
        'this', 'that', 'with', 'they', 'have', 'from', 'been', 'than', 'more',
        'very', 'when', 'much', 'some', 'time', 'way', 'may', 'said', 'each',
        'which', 'their', 'would', 'there', 'could', 'other', 'able', 'today',
        'students', 'student', 'lesson', 'class', 'grade'  # Too generic for image search
    }
    
    meaningful_words = []
    for word in words:
        word_lower = word.lower()
        if word_lower in priority_words:
            meaningful_words.append(word_lower)
        elif word_lower not in stop_words and len(word) > 4:
            meaningful_words.append(word_lower)
    
    # Build enhanced search term
    search_parts = []
    
    # Add subject context first (most important for relevance)
    if subject_context:
        search_parts.extend(subject_context[:1])  # Take the first subject
    
    # Add educational context
    if educational_context:
        search_parts.extend(educational_context[:1])
    
    # Add meaningful content words
    if meaningful_words:
        search_parts.extend(meaningful_words[:2])
    
    # Always add educational context for better classroom relevance
    if 'classroom' not in ' '.join(search_parts):
        search_parts.append('classroom')
    
    # Add visual indicator for better educational images
    search_parts.append('educational')
    
    if search_parts:
        result = ' '.join(search_parts)
        logger.info(f"Generated enhanced contextual search terms: '{result}'")
        return result
    
    # Fallback to enhanced generic educational image
    logger.info("No specific keywords found, using enhanced generic education search")
    return 'elementary classroom learning colorful educational bright'

def add_image_to_slide(slide, image_bytes, lesson_topic=""):
    """
    Add an image to a content slide with improved positioning to prevent content overlap.
    Places image on the right side, leaving clear space for content.
    """
    try:
        # Create a BytesIO object from the image bytes
        image_stream = io.BytesIO(image_bytes)
        
        # Open image with PIL to get dimensions and potentially resize
        with Image.open(image_stream) as img:
            original_width, original_height = img.size
            
            # Get slide dimensions
            slide_width = Inches(10)  # Standard slide width
            slide_height = Inches(7.5)  # Standard slide height
            
            # Position image on the right side with better proportions
            # Make content area use left 60% of slide, image uses right 35%
            target_width = Inches(3.2)   # Slightly smaller for better balance
            target_height = Inches(2.8)  # Good proportion for educational content
            
            # Calculate aspect ratio and adjust if needed
            img_aspect = original_width / original_height
            target_aspect = target_width / target_height
            
            if img_aspect > target_aspect:
                # Image is wider than target, fit by width
                final_width = target_width
                final_height = target_width / img_aspect
            else:
                # Image is taller than target, fit by height
                final_height = target_height
                final_width = target_height * img_aspect
            
            # Position on right side with proper margins
            left = slide_width - final_width - Inches(0.4)  # 0.4" margin from right edge
            top = Inches(1.5)  # Below title area, aligned with content start
            
            # Reset image stream position
            image_stream.seek(0)
            
            # Add image to slide
            picture = slide.shapes.add_picture(
                image_stream, 
                left, 
                top, 
                final_width, 
                final_height
            )
            
            # Add subtle styling for professional look
            line = picture.line
            line.color.rgb = RGBColor(220, 220, 220)  # Very light gray border
            line.width = Pt(0.75)
            
            # Optional: Add subtle shadow effect
            try:
                shadow = picture.shadow
                shadow.inherit = False
                shadow.style = 'OUTER'
                shadow.distance = Pt(3)
                shadow.blur_radius = Pt(4)
                shadow.color.rgb = RGBColor(128, 128, 128)
                shadow.transparency = 0.5
            except:
                pass  # Shadow effects might not be available in all versions
            
            logger.info(f"Successfully added image to slide with improved layout (size: {final_width} x {final_height})")
            return True
            
    except Exception as e:
        logger.error(f"Failed to add image to slide: {e}")
        return False
    finally:
        if 'image_stream' in locals():
            image_stream.close()

def generate_search_query_from_content(structured_content, fallback="elementary classroom educational"):
    """
    Generate an enhanced search query for Unsplash based on lesson content.
    Uses the new enhanced keyword extraction for better image relevance.
    """
    try:
        if not structured_content or len(structured_content) == 0:
            return fallback
        
        # Use the enhanced keyword extraction
        enhanced_query = extract_enhanced_search_keywords(structured_content)
        
        if enhanced_query and enhanced_query != fallback:
            logger.info(f"Using enhanced search query: '{enhanced_query}'")
            return enhanced_query
        
        # Fallback to original logic if enhanced extraction doesn't find anything
        # Find the first slide with meaningful content (skip title-only slides)
        content_slide = None
        for slide in structured_content:
            content_items = slide.get('content', [])
            if content_items and len(content_items) > 0:
                # Check if this slide has real content, not just titles
                has_real_content = any(
                    len(item.strip()) > 10 and 
                    not item.lower().startswith(('students will', 'today we will', 'objectives'))
                    for item in content_items
                )
                if has_real_content:
                    content_slide = slide
                    break
        
        # If no content slide found, use the first slide
        if not content_slide:
            content_slide = structured_content[0]
        
        # Get title and content from the selected slide
        title = content_slide.get('title', '').lower()
        content_items = content_slide.get('content', [])
        content_text = ' '.join(content_items).lower() if content_items else ''
        
        # Combine title and content for analysis
        combined_text = f"{title} {content_text}".strip()
        
        # Look for specific topics in the title or content with enhanced mapping
        if 'equivalent' in combined_text and 'fraction' in combined_text:
            return "mathematics fractions equivalent classroom educational"
        elif 'place value' in combined_text:
            return "place value chart mathematics classroom educational"
        elif 'photosynthesis' in combined_text:
            return "photosynthesis plant science classroom educational"
        
        # Extract subject-related keywords with enhanced comprehensive mapping
        subject_keywords = {
            'mathematics': ['math', 'mathematics', 'number', 'fraction', 'algebra', 'geometry', 'calculation', 'equation', 'addition', 'subtraction', 'multiplication', 'division', 'decimal', 'percentage'],
            'science': ['science', 'biology', 'chemistry', 'physics', 'experiment', 'hypothesis', 'molecule', 'atom', 'cell', 'gravity', 'energy', 'plant', 'animal'],
            'reading': ['reading', 'writing', 'literature', 'grammar', 'vocabulary', 'story', 'essay', 'book', 'novel', 'poem', 'letter', 'word'],
            'history': ['history', 'historical', 'ancient', 'civilization', 'war', 'timeline', 'century', 'revolution', 'empire'],
            'geography': ['geography', 'continent', 'country', 'map', 'climate', 'population', 'city', 'ocean', 'mountain'],
            'art': ['art', 'painting', 'drawing', 'color', 'creativity', 'design', 'artistic', 'brush', 'canvas'],
            'music': ['music', 'song', 'rhythm', 'instrument', 'melody', 'sound', 'musical', 'note', 'piano']
        }
        
        # Find matching subjects
        detected_subjects = []
        for subject, keywords in subject_keywords.items():
            if any(keyword in combined_text for keyword in keywords):
                detected_subjects.append(subject)
        
        # Generate query based on detected subjects
        if detected_subjects:
            primary_subject = detected_subjects[0]
            
            # Add more specific terms based on content and grade level
            if any(term in combined_text for term in ['kindergarten', 'young', 'children']):
                return f"{primary_subject} children classroom educational"
            elif any(term in combined_text for term in ['elementary', 'primary']):
                return f"{primary_subject} elementary school educational"
            elif any(term in combined_text for term in ['middle', 'junior']):
                return f"{primary_subject} middle school educational"
            elif any(term in combined_text for term in ['high', 'secondary']):
                return f"{primary_subject} high school educational"
            else:
                return f"{primary_subject} education classroom colorful"
        
        # If no subjects detected, look for general educational terms
        educational_terms = ['learn', 'teach', 'school', 'class', 'lesson', 'study', 'education', 'student']
        if any(term in combined_text for term in educational_terms):
            return "classroom learning students educational bright"
        
        # Final enhanced fallback
        return "elementary classroom learning educational colorful"
        
    except Exception as e:
        logger.error(f"Error generating search query: {e}")
        return fallback

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

def add_text_box_to_slide(slide, content_items, with_image=False):
    """Add a text box to the slide with improved positioning when images are present"""
    # Adjust text box position and size for better layout with images
    if with_image:
        # Make text box narrower and positioned to avoid image on the right
        left = Inches(0.5)
        top = Inches(2)
        width = Inches(5.8)  # Narrower to leave clear space for image (60% of slide)
        height = Inches(4.5)
    else:
        # Use more of the slide if no image
        left = Inches(1)
        top = Inches(2)
        width = Inches(8)
        height = Inches(5)
    
    textbox = slide.shapes.add_textbox(left, top, width, height)
    text_frame = textbox.text_frame
    text_frame.clear()
    
    # Improve text frame properties for better readability
    text_frame.margin_left = Inches(0.1)
    text_frame.margin_right = Inches(0.1)
    text_frame.margin_top = Inches(0.1)
    text_frame.margin_bottom = Inches(0.1)
    text_frame.word_wrap = True
    
    # Use cleaned content
    cleaned_items = clean_content_list_for_presentation(content_items)
    
    for item in cleaned_items:
        p = text_frame.add_paragraph()
        p.text = f"• {item}"
        p.font.name = STYLE['fonts']['body']
        p.font.size = STYLE['sizes']['body']
        p.font.color.rgb = STYLE['colors']['body']
        p.space_after = Pt(6)  # Add some space between bullet points
    
    logger.info(f"Added text box to slide ({'with image accommodation' if with_image else 'full width'})")

def create_clean_presentation_with_images(structured_content, include_images=True):
    """Create a PowerPoint presentation from clean structured content with enhanced images"""
    # Reset the image tracking flag
    if hasattr(create_clean_presentation_with_images, '_image_added'):
        delattr(create_clean_presentation_with_images, '_image_added')
    
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
    
    # Initialize Unsplash service if images are requested
    unsplash_photo_data = None
    image_bytes = None
    
    if include_images:
        try:
            from src.services.unsplash_service import unsplash_service
            
            # Generate enhanced search query from lesson content
            search_query = generate_search_query_from_content(structured_content)
            logger.info(f"Searching for image with enhanced query: '{search_query}'")
            
            # Search for image
            unsplash_photo_data = unsplash_service.search_photo(search_query)
            
            if unsplash_photo_data:
                # Download image
                image_bytes = unsplash_service.download_photo(unsplash_photo_data)
                if image_bytes:
                    logger.info(f"Successfully retrieved relevant image by {unsplash_photo_data['photographer_name']} for query '{search_query}'")
                else:
                    logger.warning("Failed to download image from Unsplash")
            else:
                logger.warning(f"No suitable image found for enhanced query: '{search_query}'")
                
        except Exception as e:
            logger.error(f"Error fetching image from Unsplash: {e}")
            include_images = False  # Disable images for this generation
    
    # Log available slide layouts for debugging
    logger.info(f"Available slide layouts: {len(prs.slide_layouts)}")
    for i, layout in enumerate(prs.slide_layouts):
        try:
            layout_name = layout.name if hasattr(layout, 'name') else f"Layout {i}"
            logger.debug(f"Layout {i}: {layout_name} - {len(layout.placeholders)} placeholders")
        except:
            logger.debug(f"Layout {i}: Unknown layout")
    
    # Process each slide with clean structure and improved layout
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
            
            # Add image to first content slide (skip logo/title slides) with enhanced relevance
            has_image = False
            if include_images and image_bytes:
                # Check if this is the first slide with actual content
                slide_content = slide_data.get('content', [])
                clean_content = clean_content_list_for_presentation(slide_content)
                
                # Add image to first slide that has meaningful content
                if clean_content and not hasattr(create_clean_presentation_with_images, '_image_added'):
                    has_image = add_image_to_slide(slide, image_bytes, slide_data.get('title', ''))
                    # Mark that we've added an image to prevent adding to multiple slides
                    create_clean_presentation_with_images._image_added = True
                    logger.info(f"Added enhanced relevant image to slide {slide_index + 1} (first content slide)")
            
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
            
            # Clean and add content with improved layout for images
            raw_content_items = slide_data.get('content', [])
            clean_content_items = clean_content_list_for_presentation(raw_content_items)
            
            if clean_content_items:
                content_placeholder = find_content_placeholder(slide)
                
                if content_placeholder:
                    try:
                        text_frame = content_placeholder.text_frame
                        text_frame.clear()
                        
                        # Adjust text frame properties when image is present
                        if has_image:
                            # Reduce right margin to prevent overlap with image
                            text_frame.margin_right = Inches(0.3)
                            text_frame.margin_left = Inches(0.1)
                        
                        for item in clean_content_items:
                            p = text_frame.add_paragraph()
                            p.text = item
                            p.font.name = STYLE['fonts']['body']
                            p.font.size = STYLE['sizes']['body']
                            p.font.color.rgb = STYLE['colors']['body']
                            p.level = 0  # Main bullet level
                            p.space_after = Pt(6)  # Add spacing between items
                        
                        logger.debug(f"Added {len(clean_content_items)} clean content items to slide {slide_index + 1}")
                    except Exception as e:
                        logger.warning(f"Failed to add content to placeholder on slide {slide_index + 1}: {e}")
                        # Fallback to text box
                        add_text_box_to_slide(slide, clean_content_items, has_image)
                else:
                    # No suitable placeholder found, create a text box
                    logger.warning(f"No content placeholder found on slide {slide_index + 1}, using text box")
                    add_text_box_to_slide(slide, clean_content_items, has_image)
                    
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
                    add_text_box_to_slide(slide, content_items, False)
                
                logger.info(f"Created fallback slide {slide_index + 1} with text boxes")
            except Exception as fallback_error:
                logger.error(f"Failed to create fallback slide {slide_index + 1}: {fallback_error}")
    
    # Add attribution for image if used
    if include_images and unsplash_photo_data and image_bytes:
        try:
            # Add a final slide with attribution or add it to the last slide
            if len(prs.slides) > 0:
                last_slide = prs.slides[-1]
                
                # Add small attribution text at bottom
                attribution_text = f"Image: {unsplash_photo_data['photographer_name']} on Unsplash"
                
                # Add attribution as small text box at bottom
                attr_box = last_slide.shapes.add_textbox(
                    Inches(0.5), 
                    Inches(7), 
                    Inches(9), 
                    Inches(0.3)
                )
                attr_frame = attr_box.text_frame
                attr_para = attr_frame.add_paragraph()
                attr_para.text = attribution_text
                attr_para.font.size = Pt(8)
                attr_para.font.color.rgb = RGBColor(128, 128, 128)  # Gray color
                attr_para.alignment = PP_ALIGN.RIGHT
                
                logger.info(f"Added attribution: {attribution_text}")
                
        except Exception as e:
            logger.warning(f"Failed to add image attribution: {e}")
    
    logger.info(f"Created presentation with {len(structured_content)} slides (images: {'enabled' if include_images else 'disabled'})")
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
    
    return create_clean_presentation_with_images(clean_content, include_images=True)

def create_clean_presentation(structured_content):
    """Create a PowerPoint presentation from clean structured content without images"""
    return create_clean_presentation_with_images(structured_content, include_images=False)

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