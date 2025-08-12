"""
Base Specialist Agent - Common functionality for resource-specific agents
"""

import json
import re
from typing import Dict, List, Any, Optional
from src.config import logger, client

class BaseSpecialistAgent:
    """Base class for agents that create specific resource types"""
    
    def __init__(self, resource_type: str):
        self.resource_type = resource_type
        self.name = f"{resource_type.title()} Specialist Agent"
        
    def create_structured_content(self,
                                research_data: Dict[str, Any],
                                num_sections: int,
                                lesson_topic: str,
                                subject_focus: str,
                                grade_level: str,
                                language: str = "English",
                                custom_requirements: str = "") -> List[Dict[str, Any]]:
        """
        Create structured content for a specific resource type using research data
        Must return the same format as the original system: List[Dict[str, Any]]
        """
        logger.info(f"{self.name} creating content for: {lesson_topic}")
        
        system_prompt = self._get_system_prompt(language)
        user_prompt = self._build_user_prompt(
            research_data, num_sections, lesson_topic, 
            subject_focus, grade_level, language, custom_requirements
        )
        
        try:
            # Make API call to DeepSeek
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=4000,
                temperature=0.4,  # Balanced creativity and consistency
                stream=False
            )
            
            content = response.choices[0].message.content.strip()
            logger.info(f"Raw {self.resource_type} response length: {len(content)} characters")
            logger.info(f"Raw {self.resource_type} response: {content[:500]}...")
            
            # Parse the response into structured content
            structured_content = self._parse_response_to_structured_content(content, num_sections)
            
            if not structured_content:
                logger.warning(f"{self.name} parsing failed, using fallback")
                structured_content = self._create_fallback_content(
                    research_data, num_sections, lesson_topic, language
                )
            
            logger.info(f"{self.name} created {len(structured_content)} sections")
            return structured_content
            
        except Exception as e:
            logger.error(f"Error in {self.name}: {e}")
            return self._create_fallback_content(research_data, num_sections, lesson_topic, language)
    
    def _get_system_prompt(self, language: str) -> str:
        """Get the system prompt for this resource type - must be overridden"""
        raise NotImplementedError("Subclasses must implement _get_system_prompt")
    
    def _build_user_prompt(self, research_data: Dict[str, Any], num_sections: int,
                          lesson_topic: str, subject_focus: str, grade_level: str,
                          language: str, custom_requirements: str) -> str:
        """Build the user prompt using research data"""
        
        # Extract key information from research data
        core_concepts = research_data.get("core_concepts", [])
        key_points = research_data.get("key_learning_points", [])
        examples = research_data.get("age_appropriate_examples", [])
        vocab = research_data.get("vocabulary", [])
        misconceptions = research_data.get("common_misconceptions", [])
        real_world = research_data.get("real_world_connections", [])
        objectives = research_data.get("learning_objectives", [])
        teaching_tips = research_data.get("teaching_tips", [])
        
        return f"""Create a high-quality {self.resource_type} using this comprehensive research data:

TOPIC: {lesson_topic}
SUBJECT: {subject_focus}  
GRADE: {grade_level}
LANGUAGE: {language}
SECTIONS NEEDED: {num_sections}

FOUNDATIONAL RESEARCH:
Core Concepts: {', '.join(core_concepts[:4])}
Key Learning Points: {', '.join(key_points[:4])}
Real-World Examples: {', '.join(examples[:4])}
Essential Vocabulary: {', '.join([f"{v.get('term', '')}: {v.get('definition', '')}" for v in vocab[:4]])}
Common Misconceptions: {', '.join(misconceptions[:3])}
Real-World Connections: {', '.join(real_world[:3])}
Learning Objectives: {', '.join(objectives[:3])}
Teaching Tips: {', '.join(teaching_tips[:3])}

CONTENT REQUIREMENTS:
- Use grade-appropriate language and concepts
- Include concrete examples students can relate to
- Address common misconceptions naturally
- Incorporate essential vocabulary in context  
- Connect to real-world applications
- Ensure content is engaging and educational

ADDITIONAL REQUIREMENTS: {custom_requirements}

Create exactly {num_sections} sections that effectively utilize this research data for {grade_level} {subject_focus}."""
    
    def _parse_response_to_structured_content(self, content: str, expected_sections: int) -> List[Dict[str, Any]]:
        """Parse API response into structured content format"""
        
        # Try JSON parsing first for new structured format
        try:
            # Clean JSON markers
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            
            # Try to parse as JSON
            json_data = json.loads(content)
            
            # Handle presentation format
            if 'slides' in json_data and isinstance(json_data['slides'], list):
                return self._convert_slides_to_structured_content(json_data['slides'])
            
            # Handle quiz format  
            elif 'sections' in json_data and isinstance(json_data['sections'], list):
                return self._convert_quiz_sections_to_structured_content(json_data['sections'])
            
            # Handle direct array format
            elif isinstance(json_data, list):
                return json_data
                
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed: {e}, falling back to text parsing")
        except Exception as e:
            logger.warning(f"JSON structure parsing failed: {e}, falling back to text parsing")
        
        # Fall back to text parsing using the same logic as original system
        return self._parse_text_to_structured_content(content)
    
    def _parse_text_to_structured_content(self, content: str) -> List[Dict[str, Any]]:
        """Parse text content into structured format - matches original system"""
        
        # Determine section pattern based on resource type
        if self.resource_type.lower() == "presentation":
            section_pattern = r"Slide (\d+):\s*(.*)"
        else:
            section_pattern = r"Section (\d+):\s*(.*)"
        
        sections = []
        current_section = None
        
        lines = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this is a section header
            match = re.match(section_pattern, line)
            if match:
                # Save previous section
                if current_section:
                    sections.append(current_section)
                
                # Start new section
                section_title = match.group(2).strip()
                current_section = {
                    "title": section_title,
                    "layout": "TITLE_AND_CONTENT",
                    "content": []
                }
            elif line.lower() == "content:":
                # Skip content headers
                continue
            elif line.startswith('-') or line.startswith('•'):
                # This is content
                if current_section:
                    clean_content = line.lstrip('-•').strip()
                    if clean_content:
                        current_section["content"].append(clean_content)
            elif current_section and line:
                # Any other non-empty line goes to content
                current_section["content"].append(line)
        
        # Don't forget the last section
        if current_section:
            sections.append(current_section)
        
        logger.info(f"Parsed {len(sections)} sections from {self.resource_type} content")
        for i, section in enumerate(sections):
            logger.info(f"Section {i+1}: '{section.get('title', 'No title')}' with {len(section.get('content', []))} content items")
        
        # If no sections found, create fallback
        if not sections:
            sections.append({
                "title": "Generated Content",
                "layout": "TITLE_AND_CONTENT",
                "content": [line.strip() for line in lines if line.strip()]
            })
        
        return sections
    
    def _create_fallback_content(self, research_data: Dict[str, Any], 
                               num_sections: int, lesson_topic: str, 
                               language: str) -> List[Dict[str, Any]]:
        """Create fallback content when parsing fails"""
        logger.warning(f"{self.name} creating fallback content")
        
        fallback_sections = []
        core_concepts = research_data.get("core_concepts", [f"{lesson_topic} concepts"])
        
        for i in range(num_sections):
            concept = core_concepts[i % len(core_concepts)] if core_concepts else f"{lesson_topic} Section {i+1}"
            
            fallback_sections.append({
                "title": f"{concept}",
                "layout": "TITLE_AND_CONTENT",
                "content": [
                    f"Key information about {concept}",
                    f"Important details for {lesson_topic}",
                    f"Examples and applications"
                ]
            })
        
        return fallback_sections
    
    def _convert_slides_to_structured_content(self, slides: List[Dict]) -> List[Dict[str, Any]]:
        """Convert JSON slides format to structured content format"""
        structured_content = []
        
        for slide in slides:
            structured_slide = {
                "title": slide.get("title", "Untitled Slide"),
                "layout": "TITLE_AND_CONTENT",
                "content": slide.get("content", [])
            }
            structured_content.append(structured_slide)
            
        logger.info(f"Converted {len(slides)} slides to structured content")
        return structured_content
    
    def _convert_quiz_sections_to_structured_content(self, sections: List[Dict]) -> List[Dict[str, Any]]:
        """Convert JSON quiz sections format to clean structured content format"""
        structured_content = []
        
        for section in sections:
            # Clean structured format - no duplication
            section_data = {
                "title": section.get("title", "Quiz Section"),
                "layout": "TITLE_AND_CONTENT"
            }
            
            # Add structured questions directly
            if "structured_questions" in section:
                section_data["structured_questions"] = section["structured_questions"]
            
            # Add teacher guidance directly  
            if "teacher_notes" in section:
                section_data["teacher_notes"] = section["teacher_notes"]
                    
            if "differentiation_tips" in section:
                section_data["differentiation_tips"] = section["differentiation_tips"]
            
            structured_content.append(section_data)
            
        logger.info(f"Converted {len(sections)} quiz sections to clean structured content")
        return structured_content