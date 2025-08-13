"""
Optimized Worksheet Agent - Single API call with structured JSON output
Reduces response time and improves parsing reliability
"""

import json
import re
from typing import Dict, Any, List, Optional
from src.config import logger, client

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
        """Optimized system prompt with structured JSON output"""
        
        return f"""You are an expert educator who creates high-quality worksheets with structured JSON output for clean parsing.

CRITICAL: Respond with ONLY valid JSON. No explanations, no additional text.

LANGUAGE: All content in {language}
GRADE LEVEL: {grade_level} appropriate complexity and vocabulary
SUBJECT: Focus on {subject_focus} concepts and standards

OUTPUT FORMAT (respond with exactly this JSON structure):
{{
  "sections": [
    {{
      "title": "Practice Section Title in {language}",
      "questions": [
        {{
          "question": "Complete question or problem text in {language}",
          "type": "fill_blank",
          "answer": "Correct answer",
          "explanation": "Brief explanation if needed"
        }},
        {{
          "question": "Word problem or scenario in {language}",
          "type": "word_problem",
          "answer": "Solution with units",
          "explanation": "Step-by-step reasoning"
        }},
        {{
          "question": "Multiple choice question in {language}",
          "type": "multiple_choice",
          "options": ["Option A", "Option B", "Option C", "Option D"],
          "answer": "Correct option",
          "explanation": "Why this is correct"
        }}
      ],
      "teacher_notes": ["Specific implementation guidance in {language}"],
      "differentiation_tips": ["Strategies for diverse learners in {language}"]
    }}
  ]
}}

QUESTION TYPES TO USE:
- "fill_blank": Fill-in-the-blank problems
- "word_problem": Real-world application problems
- "multiple_choice": A/B/C/D format questions
- "short_answer": Brief response questions
- "calculation": Math problems requiring computation
- "matching": Connect related concepts

CONTENT REQUIREMENTS:
- Mix question types within each section
- Progress from guided practice to independent work
- Write questions directly for STUDENTS to read and answer
- Use grade-appropriate vocabulary
- Provide accurate answers and explanations
- Design for completion in reasonable time
- NEVER reference pictures, images, or visual elements that don't exist
- For visual problems, provide clear student instructions or use [Teacher: provide visual aid] format
- Questions should align with presentation and quiz content for consistency

WORKSHEET DESIGN PRINCIPLES:
- Start with guided practice, move to independent work
- Include examples or models when introducing concepts
- Provide a mix of skill levels within each section
- Create engaging, meaningful practice activities
- Use clear, simple language
- Design for formative assessment opportunities

TEACHER SUPPORT:
- Each section includes specific teaching guidance
- Each section includes differentiation strategies
- Focus on practical implementation advice
- Address common student difficulties

CLEAN JSON STRUCTURE EXAMPLE:
{{
  "sections": [
    {{
      "title": "Basic Fraction Understanding",
      "questions": [
        {{
          "question": "What fraction of this rectangle is shaded? ___/___",
          "type": "fill_blank",
          "answer": "1/4",
          "explanation": "1 part out of 4 total parts",
          "teacher_instruction": "Draw rectangle with 1 of 4 parts shaded"
        }},
        {{
          "question": "A pizza is cut into 8 equal slices. You eat 3 slices. What fraction did you eat?",
          "type": "multiple_choice",
          "options": ["3/5", "3/8", "8/3", "5/8"],
          "answer": "3/8",
          "explanation": "3 slices eaten out of 8 total slices"
        }},
        {{
          "question": "Complete the fraction: Half of 10 cookies = ___/10",
          "type": "fill_blank",
          "answer": "5/10",
          "explanation": "Half means 1 out of 2 equal parts, so 5 out of 10"
        }}
      ],
      "teacher_notes": ["Use fraction manipulatives or visual aids", "Allow 15-20 minutes"],
      "differentiation_tips": ["Provide fraction strips for visual support", "Advanced students can reduce fractions to lowest terms"]
    }}
  ]
}}

STUDENT-FOCUSED FORMATTING:
- Write questions as students would read them
- NO teacher instructions in student questions - put in separate "teacher_instruction" field
- Multiple choice options should be formatted clearly on separate lines
- Make questions clear and self-contained for student understanding
- Align with presentation and quiz content for consistency
- Prioritize content that displays without extra teacher work unless necessary for learning

OPTIMIZATION FOCUS:
- Direct, efficient content generation
- Complete questions with full context
- Ready-to-use format for worksheet handlers
- Balanced difficulty appropriate for grade level"""

    def _build_optimized_user_prompt(self, lesson_topic: str, subject_focus: str, grade_level: str,
                                   language: str, num_sections: int, standards: List[str], custom_requirements: str) -> str:
        """Streamlined user prompt for single-call efficiency"""
        
        standards_text = f"Standards: {', '.join(standards[:3])}" if standards else ""
        
        return f"""Create a {num_sections}-section worksheet on "{lesson_topic}" for {grade_level} {subject_focus}.

TOPIC: {lesson_topic}
GRADE: {grade_level}
SUBJECT: {subject_focus}
LANGUAGE: {language}
{standards_text}
{f"REQUIREMENTS: {custom_requirements}" if custom_requirements else ""}

Generate {num_sections} practice sections with varied question types.
Each section should have 3-5 questions that build skills progressively.
Include teacher notes and differentiation tips for each section.

Respond with valid JSON only."""

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