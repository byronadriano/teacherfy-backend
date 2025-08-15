"""
Optimized Worksheet Agent - Single API call with structured JSON output
Reduces response time and improves parsing reliability
"""

import json
import re
from typing import Dict, Any, List, Optional
from config.settings import logger, client
from utils.subject_guidance import SubjectSpecificPrompts

class OptimizedWorksheetAgent:
    """Single-call worksheet generation agent with structured JSON output"""
    
    def __init__(self):
        self.name = "Optimized Worksheet Agent"
        self.resource_type = "worksheet"
        
    def create_structured_content(self,
                                lesson_topic: str,
                                subject_focus: str,
                                grade_level: str,
                                language: str = "English",
                                num_sections: int = 3,
                                standards: List[str] = None,
                                custom_requirements: str = "") -> List[Dict[str, Any]]:
        """Single API call for optimized worksheet generation"""
        logger.info(f"Optimized Worksheet Agent creating {num_sections} sections for: {lesson_topic}")
        
        system_prompt = self._get_optimized_system_prompt(language, grade_level, subject_focus)
        user_prompt = self._build_optimized_user_prompt(
            lesson_topic, subject_focus, grade_level, language, 
            num_sections, standards or [], custom_requirements
        )
        
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=3500,
                temperature=0.3,
                stream=False
            )
            
            content = response.choices[0].message.content.strip()
            logger.info(f"Worksheet response length: {len(content)} characters")
            
            structured_content = self._parse_optimized_response(content, num_sections)
            
            if not structured_content:
                logger.warning("Parsing failed, using intelligent fallback")
                structured_content = self._create_intelligent_fallback(
                    lesson_topic, subject_focus, grade_level, num_sections, language
                )
            
            logger.info(f"Optimized worksheet generation complete: {len(structured_content)} sections")
            return structured_content
            
        except Exception as e:
            logger.error(f"Error in optimized worksheet generation: {e}")
            return self._create_intelligent_fallback(lesson_topic, subject_focus, grade_level, num_sections, language)

    def _get_optimized_system_prompt(self, language: str, grade_level: str, subject_focus: str) -> str:
        """Optimized system prompt with subject-specific guidance"""
        
        # Get subject-specific guidance
        subject_guidance = SubjectSpecificPrompts.format_subject_guidance_for_prompt(subject_focus, "worksheet")
        
        return f"""Expert educator creating {grade_level} worksheets in {language}. Respond with ONLY valid JSON.

{subject_guidance}

JSON FORMAT:
{{
  "sections": [
    {{
      "title": "Section Title in {language}",
      "questions": [
        {{
          "question": "Complete question in {language}",
          "type": "fill_blank|multiple_choice|short_answer|word_problem|calculation",
          "options": ["A", "B", "C", "D"] (if multiple_choice),
          "answer": "Correct answer",
          "explanation": "Brief explanation"
        }}
      ],
      "teacher_notes": ["Implementation guidance"],
      "differentiation_tips": ["Support strategies"]
    }}
  ]
}}

CONTENT RULES:
• Self-contained - no external resources needed
• Grade-appropriate vocabulary and complexity
• Progressive difficulty within sections
• Include teacher support for each section
• Mix question types for comprehensive practice"""

    def _build_optimized_user_prompt(self, lesson_topic: str, subject_focus: str, grade_level: str,
                                   language: str, num_sections: int, standards: List[str], custom_requirements: str) -> str:
        """Streamlined user prompt for single-call efficiency"""
        
        # Keep standards concise to save tokens
        standards_text = f"Standards: {', '.join(standards[:2])}" if standards else ""
        
        # Add custom requirements if provided
        custom_text = f"CUSTOM: {custom_requirements}" if custom_requirements else ""
        
        return f"""Create {num_sections}-section worksheet: "{lesson_topic}" | {grade_level} {subject_focus} | {language}

{standards_text}
{custom_text}

Generate {num_sections} sections, 3-5 questions each. Progressive difficulty. Include teacher guidance.

JSON only."""

    def _parse_optimized_response(self, content: str, expected_sections: int) -> Optional[List[Dict[str, Any]]]:
        """Parse the structured JSON response efficiently"""
        
        content = content.strip()
        
        # Remove markdown if present
        if content.startswith('```json'):
            content = content.split('```json')[1].split('```')[0].strip()
        elif content.startswith('```'):
            content = content.split('```')[1].split('```')[0].strip()
        
        try:
            json_data = json.loads(content)
            
            # Check for new structured format
            if isinstance(json_data, dict) and 'sections' in json_data:
                return self._convert_json_to_legacy_format(json_data)
                
            # Old format fallback
            elif isinstance(json_data, list):
                valid_sections = []
                for section in json_data:
                    if isinstance(section, dict) and 'title' in section and 'content' in section:
                        if 'layout' not in section:
                            section['layout'] = 'TITLE_AND_CONTENT'
                        valid_sections.append(section)
                
                if len(valid_sections) >= 1:
                    logger.info(f"Using fallback format: {len(valid_sections)} sections")
                    return valid_sections
                    
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
        except Exception as e:
            logger.error(f"Response parsing error: {e}")
            
        return None

    def _convert_json_to_legacy_format(self, json_data: Dict) -> List[Dict[str, Any]]:
        """Convert new structured JSON to legacy format for handlers"""
        
        legacy_sections = []
        sections = json_data.get('sections', [])
        
        logger.info(f"Converting {len(sections)} worksheet sections from structured JSON")
        
        for section_data in sections:
            title = section_data.get('title', 'Worksheet Section')
            questions_data = section_data.get('questions', [])
            teacher_notes = section_data.get('teacher_notes', [])
            differentiation_tips = section_data.get('differentiation_tips', [])
            
            # Create clean section format with structured data
            legacy_section = {
                'title': title,
                'layout': 'TITLE_AND_CONTENT',
                'structured_questions': questions_data,
                'teacher_notes': teacher_notes,
                'differentiation_tips': differentiation_tips
            }
            
            legacy_sections.append(legacy_section)
        
        logger.info(f"Successfully converted worksheet to clean format: {len(legacy_sections)} sections")
        return legacy_sections

    def _create_intelligent_fallback(self, lesson_topic: str, subject_focus: str, 
                                   grade_level: str, num_sections: int, language: str) -> List[Dict[str, Any]]:
        """Create intelligent fallback content"""
        logger.warning("Creating intelligent worksheet fallback content")
        
        fallback_sections = []
        for i in range(num_sections):
            fallback_sections.append({
                "title": f"{lesson_topic} - Practice {i+1}",
                "layout": "TITLE_AND_CONTENT",
                "structured_questions": [
                    {
                        "question": f"Practice problem about {lesson_topic}",
                        "type": "short_answer",
                        "answer": "Sample answer",
                        "explanation": "Brief explanation"
                    }
                ],
                "teacher_notes": [f"Guide students through {lesson_topic} practice"],
                "differentiation_tips": ["Provide additional support as needed"]
            })
        
        return fallback_sections