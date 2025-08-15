"""
Optimized Lesson Plan Agent - Single API call with structured JSON output
Reduces response time and improves parsing reliability with resource integration
"""

import json
import re
from typing import Dict, Any, List, Optional
from config.settings import logger, client

class OptimizedLessonPlanAgent:
    """Single-call lesson plan generation agent with comprehensive resource integration"""
    
    def __init__(self):
        self.name = "Optimized Lesson Plan Agent"
        self.resource_type = "lesson_plan"
        
    def create_structured_content(self,
                                lesson_topic: str,
                                subject_focus: str,
                                grade_level: str,
                                language: str = "English",
                                num_sections: int = 5,
                                standards: List[str] = None,
                                custom_requirements: str = "",
                                requested_resources: List[str] = None,
                                reference_content: Dict = None) -> List[Dict[str, Any]]:
        """Single API call for optimized lesson plan generation with resource integration"""
        logger.info(f"Optimized Lesson Plan Agent creating {num_sections} sections for: {lesson_topic}")
        
        system_prompt = self._get_optimized_system_prompt(language, grade_level, subject_focus, requested_resources)
        user_prompt = self._build_optimized_user_prompt(
            lesson_topic, subject_focus, grade_level, language, 
            num_sections, standards or [], custom_requirements, requested_resources, reference_content
        )
        
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=4000,  # Larger for comprehensive lesson plans
                temperature=0.3,
                stream=False
            )
            
            content = response.choices[0].message.content.strip()
            logger.info(f"Lesson plan response length: {len(content)} characters")
            
            structured_content = self._parse_optimized_response(content, num_sections)
            
            if not structured_content:
                logger.warning("Parsing failed, using intelligent fallback")
                structured_content = self._create_intelligent_fallback(
                    lesson_topic, subject_focus, grade_level, num_sections, language, requested_resources
                )
            
            logger.info(f"Optimized lesson plan generation complete: {len(structured_content)} sections")
            return structured_content
            
        except Exception as e:
            logger.error(f"Error in optimized lesson plan generation: {e}")
            return self._create_intelligent_fallback(lesson_topic, subject_focus, grade_level, num_sections, language, requested_resources)

    def _get_optimized_system_prompt(self, language: str, grade_level: str, subject_focus: str, requested_resources: List[str] = None) -> str:
        """Optimized system prompt with structured JSON output and resource integration"""
        
        resource_context = ""
        if requested_resources:
            resource_context = f"""
RESOURCE INTEGRATION: This lesson plan will be used alongside these resources: {', '.join(requested_resources)}
- Design activities that complement and reference these resources
- Include specific guidance for when and how to use each resource
- Create seamless transitions between lesson plan and supplementary materials"""
        
        return f"""You are an expert lesson planning specialist who creates comprehensive, ready-to-implement lesson plans with structured JSON output.

CRITICAL: Respond with ONLY valid JSON. No explanations, no additional text.

LANGUAGE: All content in {language}
GRADE LEVEL: {grade_level} appropriate complexity and activities
SUBJECT: Focus on {subject_focus} concepts and standards
{resource_context}

OUTPUT FORMAT (respond with exactly this JSON structure):
{{
  "sections": [
    {{
      "title": "Lesson Phase Title in {language}",
      "activities": [
        {{
          "activity": "Specific learning activity description in {language}",
          "type": "opening",
          "duration": "5-10 minutes",
          "materials": ["Required materials"],
          "instructions": "Step-by-step teacher instructions in {language}"
        }},
        {{
          "activity": "Main learning activity in {language}",
          "type": "instruction",
          "duration": "15-20 minutes", 
          "materials": ["Materials needed"],
          "instructions": "Detailed implementation guidance in {language}"
        }}
      ],
      "teacher_actions": ["Specific teacher moves and facilitation strategies in {language}"],
      "differentiation_tips": ["Modifications for diverse learners in {language}"],
      "assessment_checks": ["Formative assessment strategies in {language}"]
    }}
  ]
}}

ACTIVITY TYPES TO USE:
- "opening": Hook, engagement, or warm-up activities
- "instruction": Direct teaching and modeling
- "guided_practice": Teacher-supported student practice
- "independent_practice": Student-led application
- "closure": Reflection, summary, or wrap-up

LESSON PLAN COMPONENTS:
- Clear learning objectives and success criteria
- Engaging opening to capture student interest
- Scaffolded instruction with modeling
- Multiple opportunities for student practice
- Formative assessment throughout
- Meaningful closure and reflection

CONTENT REQUIREMENTS:
- Mix activity types for balanced instruction
- Include specific timing for each component
- Provide clear, actionable teacher instructions
- Use grade-appropriate language and activities
- Address diverse learning needs
- Include materials and preparation notes

TEACHER SUPPORT:
- Each section includes specific teacher actions
- Each section includes differentiation strategies
- Each section includes assessment checkpoints
- Focus on practical implementation guidance
- Address common instructional challenges

RESOURCE INTEGRATION PRINCIPLES:
- Reference when to use supplementary materials
- Create smooth transitions between activities
- Align lesson activities with resource content
- Maximize educational impact of all resources
- Use accurate slide numbers (e.g., slides 1-6 if presentation has 6 slides)
- Only reference materials that actually exist in the resources

CLEAN JSON STRUCTURE EXAMPLE:
{{
  "sections": [
    {{
      "title": "Opening and Learning Objectives",
      "activities": [
        {{
          "activity": "Welcome students and review previous learning about fractions",
          "type": "opening",
          "duration": "5 minutes",
          "materials": ["Whiteboard", "Previous day's work"],
          "instructions": "Ask students to share one thing they remember about fractions from yesterday"
        }},
        {{
          "activity": "Present today's learning objectives using presentation slides",
          "type": "instruction",
          "duration": "5 minutes",
          "materials": ["Presentation slides 1-2", "Learning objectives"],
          "instructions": "Display presentation objectives slides and read aloud together, showing real examples"
        }}
      ],
      "teacher_actions": ["Circulate to engage all students", "Use wait time for responses"],
      "differentiation_tips": ["Visual learners benefit from fraction drawings", "ELL students need vocabulary support"],
      "assessment_checks": ["Listen for fraction vocabulary usage", "Observe student engagement levels"]
    }}
  ]
}}

OPTIMIZATION FOCUS:
- Direct, actionable lesson planning guidance
- Complete activities with full implementation details
- Ready-to-use format for lesson plan handlers
- Comprehensive coverage of lesson phases
- Resource-integrated instruction when applicable"""

    def _build_optimized_user_prompt(self, lesson_topic: str, subject_focus: str, grade_level: str,
                                   language: str, num_sections: int, standards: List[str], 
                                   custom_requirements: str, requested_resources: List[str] = None,
                                   reference_content: Dict = None) -> str:
        """Streamlined user prompt with resource integration"""
        
        standards_text = f"Standards: {', '.join(standards[:3])}" if standards else ""
        resource_text = f"Resources available: {', '.join(requested_resources)}" if requested_resources else ""
        
        return f"""Create a comprehensive {num_sections}-section lesson plan on "{lesson_topic}" for {grade_level} {subject_focus}.

TOPIC: {lesson_topic}
GRADE: {grade_level}
SUBJECT: {subject_focus}
LANGUAGE: {language}
{standards_text}
{resource_text}
{f"REQUIREMENTS: {custom_requirements}" if custom_requirements else ""}

Generate {num_sections} lesson phases covering:
1. Opening/Hook (engage students)
2. Learning Objectives (clear goals)
3. Direct Instruction (teaching and modeling)
4. Guided Practice (supported application)
5. Independent Practice/Closure (assessment and reflection)

Each section should include specific activities, teacher actions, differentiation tips, and assessment strategies.
{f"Integrate references to these resources: {', '.join(requested_resources)}" if requested_resources else ""}

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
        
        logger.info(f"Converting {len(sections)} lesson plan sections from structured JSON")
        
        for section_data in sections:
            title = section_data.get('title', 'Lesson Phase')
            activities_data = section_data.get('activities', [])
            teacher_actions = section_data.get('teacher_actions', [])
            differentiation_tips = section_data.get('differentiation_tips', [])
            assessment_checks = section_data.get('assessment_checks', [])
            
            # Create clean section format with structured data
            legacy_section = {
                'title': title,
                'layout': 'TITLE_AND_CONTENT',
                'structured_activities': activities_data,
                'teacher_actions': teacher_actions,
                'differentiation_tips': differentiation_tips,
                'assessment_checks': assessment_checks
            }
            
            legacy_sections.append(legacy_section)
        
        logger.info(f"Successfully converted lesson plan to clean format: {len(legacy_sections)} sections")
        return legacy_sections

    def _create_intelligent_fallback(self, lesson_topic: str, subject_focus: str, 
                                   grade_level: str, num_sections: int, language: str,
                                   requested_resources: List[str] = None) -> List[Dict[str, Any]]:
        """Create intelligent fallback content with resource integration"""
        logger.warning("Creating intelligent lesson plan fallback content")
        
        lesson_phases = [
            "Opening and Objectives",
            "Direct Instruction",
            "Guided Practice",
            "Independent Practice",
            "Closure and Reflection"
        ]
        
        fallback_sections = []
        for i in range(num_sections):
            phase_name = lesson_phases[i] if i < len(lesson_phases) else f"Additional Activity {i+1}"
            
            section = {
                "title": f"{phase_name}: {lesson_topic}",
                "layout": "TITLE_AND_CONTENT",
                "structured_activities": [
                    {
                        "activity": f"Engage students in learning about {lesson_topic}",
                        "type": "instruction",
                        "duration": "10-15 minutes",
                        "materials": ["Basic classroom materials"],
                        "instructions": f"Guide students through {lesson_topic} concepts appropriate for {grade_level}"
                    }
                ],
                "teacher_actions": [f"Facilitate {lesson_topic} learning activities"],
                "differentiation_tips": ["Provide support for diverse learners"],
                "assessment_checks": ["Monitor student understanding"]
            }
            
            # Add resource integration if available
            if requested_resources:
                section["structured_activities"][0]["instructions"] += f". Reference {', '.join(requested_resources)} as needed."
            
            fallback_sections.append(section)
        
        return fallback_sections