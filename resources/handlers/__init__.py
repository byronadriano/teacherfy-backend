# resources/handlers/__init__.py
from .presentation_handler import PresentationHandler
from .lesson_plan_handler import LessonPlanHandler
from .worksheet_handler import WorksheetHandler
from .quiz_handler import QuizHandler

__all__ = [
    'PresentationHandler', 
    'LessonPlanHandler',
    'WorksheetHandler',
    'QuizHandler'
]