# src/resource_types.py
from enum import Enum

class ResourceType(Enum):
    PRESENTATION = "presentation"
    LESSON_PLAN = "lesson_plan"
    WORKSHEET = "worksheet" 
    QUIZ = "quiz"

def get_resource_handler(resource_type, structured_content):
    """Get the appropriate resource handler for the given type"""
    from src.resource_handlers import (
        PresentationHandler, 
        LessonPlanHandler, 
        WorksheetHandler, 
        QuizHandler
    )
    
    # Convert string to enum if needed
    if isinstance(resource_type, str):
        try:
            resource_type = ResourceType(resource_type.lower())
        except ValueError:
            raise ValueError(f"Invalid resource type: {resource_type}")
    
    # Map resource types to handlers
    handlers = {
        ResourceType.PRESENTATION: PresentationHandler,
        ResourceType.LESSON_PLAN: LessonPlanHandler,
        ResourceType.WORKSHEET: WorksheetHandler,
        ResourceType.QUIZ: QuizHandler
    }
    
    # Get the handler class
    handler_class = handlers.get(resource_type)
    if not handler_class:
        raise ValueError(f"No handler available for resource type: {resource_type}")
    
    # Create and return an instance of the handler
    return handler_class(structured_content)