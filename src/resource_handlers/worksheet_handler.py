# src/resource_handlers/worksheet_handler.py
import os
import logging
import docx
import re
from typing import Dict, Any, List, Optional
from .base_handler import BaseResourceHandler

logger = logging.getLogger(__name__)

class WorksheetHandler(BaseResourceHandler):
    """Handler for generating worksheets as Word documents"""
    
    def generate(self) -> str:
        """Generate a worksheet docx file that properly handles multi-section content"""
        # Create temp file
        temp_file = self.create_temp_file("docx")
        
        # Create a new document
        doc = docx.Document()
        
        # Determine if we have embedded sections in a single content item
        # or multiple properly separated sections
        sections = []
        
        if len(self.structured_content) == 1 and len(self.structured_content[0].get('content', [])) > 0:
            # We likely have embedded sections in a single content item
            main_item = self.structured_content[0]
            title = main_item.get('title', 'Worksheet')
            
            # Add the main title
            doc.add_heading(title, 0)
            
            # Add name and date fields
            doc.add_paragraph('Name: _________________________________ Date: _________________')
            
            # Extract sections from the content
            content_text = "\n".join(main_item.get('content', []))
            teacher_notes = "\n".join(main_item.get('teacher_notes', []))
            
            # Look for section headers
            section_matches = list(re.finditer(r"(?:^|\n)(?:\*\*)?Section\s+(\d+):\s*([^\n*]+)(?:\*\*)?", content_text))
            
            if section_matches:
                # We have properly structured sections embedded in the content
                logger.info(f"Found {len(section_matches)} embedded sections in worksheet content")
                
                for i, match in enumerate(section_matches):
                    section_num = match.group(1)
                    section_title = match.group(2).strip()
                    
                    # Get the content between this section and the next
                    start_pos = match.end()
                    end_pos = content_text.find(f"Section {int(section_num) + 1}:", start_pos)
                    if end_pos == -1:
                        # Last section
                        section_content = content_text[start_pos:]
                    else:
                        section_content = content_text[start_pos:end_pos]
                    
                    # Extract instructions and content
                    instructions = []
                    content = []
                    
                    # Find instructions
                    instr_match = re.search(r"Instructions:(.*?)(?:Content:|$)", section_content, re.DOTALL)
                    if instr_match:
                        instructions = [line.strip() for line in instr_match.group(1).strip().split('\n') 
                                      if line.strip() and not line.strip().startswith('- ')]
                    
                    # Find content items
                    content_match = re.search(r"Content:(.*?)(?:Teacher Notes:|$)", section_content, re.DOTALL)
                    if content_match:
                        content = [line.strip().lstrip('- ') for line in content_match.group(1).strip().split('\n') 
                                 if line.strip()]
                    
                    # Find related teacher notes for this section
                    notes = []
                    section_notes_match = re.search(f"Section {section_num}:.*?Teacher Notes:(.*?)(?:Section|$)", 
                                                  teacher_notes, re.DOTALL)
                    if section_notes_match:
                        notes = [line.strip().lstrip('- ') for line in section_notes_match.group(1).strip().split('\n') 
                               if line.strip()]
                    
                    sections.append({
                        'title': section_title,
                        'instructions': instructions,
                        'content': content,
                        'teacher_notes': notes
                    })
            else:
                # No clear section headers, create a single section
                instructions = main_item.get('instructions', [])
                if not instructions:
                    # Try to extract instructions
                    instr_match = re.search(r"Instructions:(.*?)(?:Content:|$)", content_text, re.DOTALL)
                    if instr_match:
                        instructions = [line.strip().lstrip('-* ') for line in instr_match.group(1).strip().split('\n') 
                                      if line.strip()]
                
                sections.append({
                    'title': 'Worksheet Activities',
                    'instructions': instructions,
                    'content': main_item.get('content', []),
                    'teacher_notes': main_item.get('teacher_notes', [])
                })
        else:
            # We already have properly separated sections
            # Add the main title from the first section
            title = self.structured_content[0].get('title', 'Worksheet') if self.structured_content else 'Worksheet'
            doc.add_heading(title, 0)
            
            # Add name and date fields
            doc.add_paragraph('Name: _________________________________ Date: _________________')
            
            # Process each section
            for item in self.structured_content:
                sections.append({
                    'title': item.get('title', 'Section'),
                    'instructions': item.get('instructions', []),
                    'content': item.get('content', []),
                    'teacher_notes': item.get('teacher_notes', [])
                })
        
        # Now process each section and add to the document
        for i, section in enumerate(sections):
            # Add section heading
            doc.add_heading(section['title'], level=1)
            
            # Add instructions if available
            if section['instructions']:
                p = doc.add_paragraph()
                p.add_run('Instructions: ').bold = True
                p.add_run(section['instructions'][0] if len(section['instructions']) > 0 else 
                        "Complete the following activities.")
                
                # Add additional instruction points if any
                for instr in section['instructions'][1:]:
                    p = doc.add_paragraph()
                    p.add_run(f"• {instr}")
            
            # Process different content types
            content_items = section['content']
            
            # Check if this is a fill-in-the-blank section
            has_blanks = any('_______' in item for item in content_items)
            has_word_bank = any('Word Bank' in item for item in content_items)
            
            # Check if this is a matching exercise
            has_matching = any(re.match(r'^\d+\.', item) for item in content_items) and \
                        any(re.match(r'^[A-Z]\.', item) for item in content_items)
            
            # Check if this is a question-answer section
            has_questions = any(item.endswith('?') for item in content_items)
            
            if has_blanks:
                # Add fill-in-the-blank items with word bank
                for item in content_items:
                    if 'Word Bank' in item:
                        # Word bank goes in its own paragraph
                        p = doc.add_paragraph()
                        p.add_run(f"{item}").bold = True
                    elif '_______' in item:
                        # Fill-in-the-blank question
                        p = doc.add_paragraph()
                        p.add_run(item)
                    else:
                        # Regular item
                        p = doc.add_paragraph()
                        p.add_run(f"{item}")
            elif has_matching:
                # Handle matching exercise
                left_items = []
                right_items = []
                
                for item in content_items:
                    if re.match(r'^\d+\.', item):
                        left_items.append(item)
                    elif re.match(r'^[A-Z]\.', item):
                        right_items.append(item)
                    elif not item.strip():
                        continue
                    else:
                        # Other content
                        p = doc.add_paragraph()
                        p.add_run(item)
                
                # Create a simple matching setup with space for answers
                if left_items and right_items:
                    table = doc.add_table(rows=max(len(left_items), len(right_items)), cols=2)
                    
                    for i, item in enumerate(left_items):
                        if i < len(table.rows):
                            table.rows[i].cells[0].text = item
                    
                    for i, item in enumerate(right_items):
                        if i < len(table.rows):
                            table.rows[i].cells[1].text = item
            
            elif has_questions:
                # Question-answer section
                for item in content_items:
                    if item.endswith('?'):
                        # It's a question
                        p = doc.add_paragraph()
                        p.add_run(item)
                        
                        # Add space for answer
                        doc.add_paragraph("_______________________________________________________")
                        doc.add_paragraph("_______________________________________________________")
                    elif '[Include' in item:
                        # This is a placeholder for content
                        p = doc.add_paragraph()
                        p.add_run(f"[Teacher: {item}]").italic = True
                    else:
                        # Regular content
                        p = doc.add_paragraph()
                        p.add_run(item)
            else:
                # Add regular content items
                for item in content_items:
                    p = doc.add_paragraph()
                    p.add_run(item)
            
            # Add extra space between sections
            if i < len(sections) - 1:
                doc.add_paragraph()
        
        # Save the document
        doc.save(temp_file)
        
        # Verify file was created and is not empty
        if not os.path.exists(temp_file):
            raise FileNotFoundError(f"Failed to create worksheet file at {temp_file}")
            
        file_size = os.path.getsize(temp_file)
        logger.info(f"Generated worksheet file size: {file_size} bytes")
        
        if file_size == 0:
            raise ValueError("Generated worksheet file is empty")
            
        return temp_file