# src/resource_types.py
from enum import Enum, auto

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
        normalized = resource_type_str.lower().replace(" ", "_")
        
        # Try to find a matching enum value
        for member in cls:
            if member.value == normalized or member.name.lower() == normalized:
                return member
        
        # Default to presentation if no match
        return cls.PRESENTATION

def get_resource_handler(resource_type, structured_content):
    """Get the appropriate resource handler for the specified type"""
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
    
    # Create and return an instance
    return handler_class(structured_content)