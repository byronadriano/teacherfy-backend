# src/resource_handlers/base_handler.py
import os
import tempfile
import time
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class BaseResourceHandler:
    """Base class for all resource handlers"""
    
    def __init__(self, structured_content: List[Dict[str, Any]]):
        self.structured_content = structured_content
        
    def generate(self) -> str:
        """Generate the resource file and return the file path"""
        raise NotImplementedError("Subclasses must implement this")
    
    def create_temp_file(self, extension: str) -> str:
        """Create a temporary file with unique name"""
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f"resource_{os.getpid()}_{int(time.time())}.{extension}")
        logger.info(f"Creating temporary file at: {temp_file}")
        return temp_file