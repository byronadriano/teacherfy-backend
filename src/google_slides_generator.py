import logging
from typing import List, Dict, Tuple, Any
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

def format_content_list(content: List[str]) -> str:
    """Format a list of content items into a properly formatted string."""
    if not content:
        return ""
    return "\n• " + "\n• ".join(str(item).strip() for item in content if item)

def format_teacher_notes(notes: List[str]) -> str:
    """Format teacher notes into a properly formatted string."""
    if not notes:
        return ""
    return "Teacher Notes:\n• " + "\n• ".join(str(note).strip() for note in notes if note)

def get_layout_for_content(slide_content: Dict[str, Any]) -> str:
    """Determine the appropriate slide layout based on content structure."""
    if slide_content.get('layout') == 'TWO_COLUMNS':
        return 'TWO_COLUMNS'
    if any(slide_content.get(key) for key in ['left_column', 'right_column']):
        return 'TWO_COLUMNS'
    return 'TITLE_AND_BODY'

def create_text_box_request(slide_id: str, text: str, transform: Dict[str, Any]) -> Dict[str, Any]:
    """Create a request to add a text box to a slide."""
    return {
        'createShape': {
            'objectId': f"{slide_id}_textbox_{hash(text) % 10000}",
            'shapeType': 'TEXT_BOX',
            'elementProperties': {
                'pageObjectId': slide_id,
                'size': {
                    'width': {'magnitude': 4000000, 'unit': 'EMU'},
                    'height': {'magnitude': 1000000, 'unit': 'EMU'}
                },
                'transform': transform
            }
        }
    }

def set_presentation_permissions(credentials: Credentials, presentation_id: str) -> None:
    """Set appropriate permissions for the presentation to ensure it can be opened."""
    try:
        drive_service = build('drive', 'v3', credentials=credentials)
        
        # Update the file to be accessible by the owner
        drive_service.files().update(
            fileId=presentation_id,
            body={
                'writersCanShare': True
            }
        ).execute()
        
        logger.info(f"Set permissions for presentation: {presentation_id}")
        
    except HttpError as error:
        logger.warning(f"Could not set permissions for presentation {presentation_id}: {error}")
    except Exception as e:
        logger.warning(f"Unexpected error setting permissions: {e}")

def create_google_slides_presentation(credentials: Credentials, 
                                    structured_content: List[Dict[str, Any]]) -> Tuple[str, str]:
    """
    Creates a Google Slides presentation based on structured content.

    Args:
        credentials: Google OAuth2 Credentials object.
        structured_content: List of dictionaries containing slide data.

    Returns:
        presentation_url: URL of the created Google Slides presentation.
        presentation_id: ID of the created presentation.
    """
    try:
        slides_service = build('slides', 'v1', credentials=credentials)
        
        # Step 1: Create presentation
        presentation = slides_service.presentations().create(body={
            'title': 'Lesson Plan'
        }).execute()
        presentation_id = presentation.get('presentationId')
        logger.info(f"Created presentation: {presentation_id}")
        
        # Step 2: Create slides with appropriate layouts
        requests = []
        for slide in structured_content:
            layout = get_layout_for_content(slide)
            requests.append({
                'createSlide': {
                    'slideLayoutReference': {
                        'predefinedLayout': layout
                    },
                    'placeholderIdMappings': []
                }
            })
        
        # Execute slide creation
        slides_service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={'requests': requests}
        ).execute()
        
        # Get updated presentation
        presentation = slides_service.presentations().get(
            presentationId=presentation_id
        ).execute()
        slides = presentation.get('slides', [])
        
        # Step 3: Populate slides
        for idx, (slide_object, slide_content) in enumerate(zip(slides[1:], structured_content)):
            slide_id = slide_object.get('objectId')
            populate_requests = []
            
            # Add title
            title = slide_content.get('title', 'Untitled Slide')
            populate_requests.append({
                'insertText': {
                    'objectId': slide_id,
                    'text': title,
                    'insertionIndex': 0
                }
            })
            
            # Handle different layout types
            if get_layout_for_content(slide_content) == 'TWO_COLUMNS':
                # Left column
                left_content = format_content_list(slide_content.get('left_column', []))
                if left_content:
                    left_transform = {
                        'scaleX': 1, 'scaleY': 1,
                        'translateX': 1000000, 'translateY': 1500000,
                        'unit': 'EMU'
                    }
                    populate_requests.append(create_text_box_request(slide_id, left_content, left_transform))
                
                # Right column
                right_content = format_content_list(slide_content.get('right_column', []))
                if right_content:
                    right_transform = {
                        'scaleX': 1, 'scaleY': 1,
                        'translateX': 5000000, 'translateY': 1500000,
                        'unit': 'EMU'
                    }
                    populate_requests.append(create_text_box_request(slide_id, right_content, right_transform))
            else:
                # Regular content
                content = format_content_list(slide_content.get('content', []))
                if content:
                    populate_requests.append({
                        'insertText': {
                            'objectId': slide_id,
                            'text': content,
                            'insertionIndex': 0
                        }
                    })
            
            # Add teacher notes
            teacher_notes = format_teacher_notes(slide_content.get('teacher_notes', []))
            if teacher_notes:
                populate_requests.append({
                    'updatePageProperties': {
                        'objectId': slide_id,
                        'pageProperties': {
                            'notesPage': {
                                'speakerNotesObjectId': f"{slide_id}_notes"
                            }
                        },
                        'fields': 'notesPage.speakerNotesObjectId'
                    }
                })
                populate_requests.append({
                    'insertText': {
                        'objectId': f"{slide_id}_notes",
                        'text': teacher_notes
                    }
                })
            
            # Add visual elements placeholder text
            visual_elements = slide_content.get('visual_elements', [])
            if visual_elements:
                notes = "\n\nSuggested Visual Elements:\n• " + "\n• ".join(visual_elements)
                if teacher_notes:
                    populate_requests.append({
                        'insertText': {
                            'objectId': f"{slide_id}_notes",
                            'text': notes,
                            'insertionIndex': len(teacher_notes)
                        }
                    })
            
            # Execute updates for this slide
            if populate_requests:
                slides_service.presentations().batchUpdate(
                    presentationId=presentation_id,
                    body={'requests': populate_requests}
                ).execute()
        
        # Set proper permissions for the presentation
        set_presentation_permissions(credentials, presentation_id)
        
        presentation_url = f"https://docs.google.com/presentation/d/{presentation_id}"
        logger.info(f"Generated presentation: {presentation_url}")
        
        return presentation_url, presentation_id
        
    except HttpError as error:
        logger.error(f"Google Slides API error: {error}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise