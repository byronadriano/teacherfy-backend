# src/utils/constants.py
"""Application constants."""

import os

# Usage limits
MONTHLY_GENERATION_LIMIT = int(os.getenv('MONTHLY_GENERATION_LIMIT', 5))
MONTHLY_DOWNLOAD_LIMIT = int(os.getenv('MONTHLY_DOWNLOAD_LIMIT', 5))

# File types
SUPPORTED_FILE_TYPES = {
    'presentation': '.pptx',
    'lesson_plan': '.docx',
    'worksheet': '.docx',
    'quiz': '.docx'
}

# MIME types for downloads
MIME_TYPES = {
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.pdf': 'application/pdf'
}

# Educational keywords for image search
EDUCATIONAL_KEYWORDS = {
    'math': 'mathematics classroom educational',
    'science': 'science classroom educational',
    'reading': 'reading classroom educational',
    'history': 'history classroom educational',
    'geography': 'geography classroom educational'
}

# Default values
DEFAULT_RESOURCE_TYPE = 'presentation'
DEFAULT_NUM_SLIDES = 5
DEFAULT_LANGUAGE = 'English'