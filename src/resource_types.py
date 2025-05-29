# src/resource_types.py - Updated with image support
from enum import Enum, auto
import logging

logger = logging.getLogger(__name__)

class ResourceType(Enum):
    """Enum for different resource types"""
    PRESENTATION = "presentation"
    LESSON_PLAN = "lesson_plan"
    WORKSHEET = "worksheet"
    QUIZ = "quiz"
    
    @classmethod
    def from_string(cls, resource_type_str):
        """Convert string to ResourceType enum"""
        if not resource_type_str:
            return cls.PRESENTATION  # Default
        
        # Normalize the string (lowercase, remove spaces)
        normalized = resource_type_str.lower().replace(" ", "_").replace("/", "_")
        
        # Special case for Quiz/Test
        if "quiz" in normalized or "test" in normalized:
            logger.info(f"Resource type '{resource_type_str}' matched to QUIZ")
            return cls.QUIZ
        
        # Special case for Lesson Plan
        if "lesson" in normalized and "plan" in normalized:
            logger.info(f"Resource type '{resource_type_str}' matched to LESSON_PLAN")
            return cls.LESSON_PLAN
            
        # Special case for Worksheet
        if "worksheet" in normalized or "activity" in normalized:
            logger.info(f"Resource type '{resource_type_str}' matched to WORKSHEET")
            return cls.WORKSHEET
            
        # Special case for Presentation
        if "presentation" in normalized or "slide" in normalized:
            logger.info(f"Resource type '{resource_type_str}' matched to PRESENTATION")
            return cls.PRESENTATION
        
        # Try to find a matching enum value
        for member in cls:
            if member.value == normalized or member.name.lower() == normalized:
                return member
        
        # Default to presentation if no match
        logger.warning(f"Unrecognized resource type: {resource_type_str}, defaulting to PRESENTATION")
        return cls.PRESENTATION

def get_resource_handler(resource_type, structured_content, **kwargs):
    """Get the appropriate resource handler for the specified type with optional parameters"""
    from src.resource_handlers import (
        PresentationHandler, 
        LessonPlanHandler,
        WorksheetHandler,
        QuizHandler
    )
    
    # Convert string to enum if needed
    if isinstance(resource_type, str):
        resource_type = ResourceType.from_string(resource_type)
    
    # Map resource types to handlers
    handlers = {
        ResourceType.PRESENTATION: PresentationHandler,
        ResourceType.LESSON_PLAN: LessonPlanHandler,
        ResourceType.WORKSHEET: WorksheetHandler,
        ResourceType.QUIZ: QuizHandler
    }
    
    # Get the handler class
    handler_class = handlers.get(resource_type, PresentationHandler)
    
    # Log which handler is being used
    logger.info(f"Using resource handler: {handler_class.__name__}")
    
    # Create and return an instance with optional parameters
    if handler_class == PresentationHandler:
        # Pass image preference for presentations
        include_images = kwargs.get('include_images', True)
        return handler_class(structured_content, include_images=include_images)
    else:
        # Other handlers don't need image support yet
        return handler_class(structured_content)