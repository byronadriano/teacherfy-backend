# google_slides_generator.py
import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

def create_google_slides_presentation(credentials, structured_content):
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
        
        # Step 1: Create a new Google Slides presentation
        presentation = slides_service.presentations().create(body={'title': 'New Lesson Plan'}).execute()
        presentation_id = presentation.get('presentationId')
        logger.info(f"Created Google Slides presentation with ID: {presentation_id}")
        
        # Step 2: Prepare batchUpdate requests based on structured_content
        requests = []
        
        for slide in structured_content:
            # Create a new slide with a predefined layout
            requests.append({
                'createSlide': {
                    'slideLayoutReference': {
                        'predefinedLayout': 'TITLE_AND_BODY'
                    }
                }
            })
        
        # Execute the batchUpdate to create slides
        slides_service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={'requests': requests}
        ).execute()
        
        # Fetch the updated presentation to get slide IDs
        presentation = slides_service.presentations().get(presentationId=presentation_id).execute()
        slides = presentation.get('slides', [])
        
        # Step 3: Populate each slide with content
        populate_requests = []
        
        for idx, slide_content in enumerate(structured_content):
            # Adjust slide indexing based on the layout
            slide_object = slides[idx + 1]  # +1 because the first slide is the title slide
            slide_id = slide_object.get('objectId')
            
            # Insert Title
            populate_requests.append({
                'insertText': {
                    'objectId': slide_id,
                    'text': f"{slide_content.get('title', 'No Title')}",
                    'insertionIndex': 0
                }
            })
            
            # Insert Content
            content = slide_content.get('content', '')
            if content:
                populate_requests.append({
                    'insertText': {
                        'objectId': slide_id,
                        'text': content,
                        'insertionIndex': 0  # Adjust as needed
                    }
                })
            
            # Insert Teacher Notes (as speaker notes)
            teacher_notes = slide_content.get('teacher_notes', '')
            if teacher_notes:
                # Google Slides API does not have a direct method to add speaker notes via batchUpdate
                # As a workaround, you can use the Slides API to add speaker notes via the 'pageProperties'
                populate_requests.append({
                    'updatePageProperties': {
                        'objectId': slide_id,
                        'pageProperties': {
                            'speakerNotes': teacher_notes
                        },
                        'fields': 'speakerNotes'
                    }
                })
            
            # Insert Visual Elements (assumed to be image URLs)
            visual_elements = slide_content.get('visual_elements', [])
            for element_url in visual_elements:
                populate_requests.append({
                    'createImage': {
                        'url': element_url,
                        'elementProperties': {
                            'pageObjectId': slide_id,
                            'size': {
                                'height': {'magnitude': 3000000, 'unit': 'EMU'},
                                'width': {'magnitude': 3000000, 'unit': 'EMU'}
                            },
                            'transform': {
                                'scaleX': 1,
                                'scaleY': 1,
                                'translateX': 1000000,
                                'translateY': 1000000,
                                'unit': 'EMU'
                            }
                        }
                    }
                })
        
        # Execute the batchUpdate to populate slides
        slides_service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={'requests': populate_requests}
        ).execute()
        
        # Step 4: Generate the presentation URL
        presentation_url = f"https://docs.google.com/presentation/d/{presentation_id}/edit"
        
        logger.info(f"Generated Google Slides presentation URL: {presentation_url}")
        
        return presentation_url, presentation_id
    except HttpError as error:
        logger.error(f"Google Slides API error: {error}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise
