"""
Agent Coordinator - Optimized single-call approach for fast educational content generation
"""

from typing import Dict, List, Any
from src.config import logger
from .optimized_quiz_agent import OptimizedQuizAgent
from .presentation_specialist_agent import (
    PresentationSpecialistAgent, 
    WorksheetSpecialistAgent,
    LessonPlanSpecialistAgent
)

class AgentCoordinator:
    """Optimized coordinator using single API calls for faster response times"""
    
    def __init__(self):
        self.specialist_agents = {
            "presentation": PresentationSpecialistAgent(),
            "quiz": OptimizedQuizAgent(),  # Optimized single-call quiz generation
            "worksheet": WorksheetSpecialistAgent(),
            "lesson_plan": LessonPlanSpecialistAgent()
        }
        logger.info("Agent Coordinator initialized with optimized single-call agents")
    
    def generate_structured_content(self,
                                  lesson_topic: str,
                                  subject_focus: str,
                                  grade_level: str,
                                  resource_type: str = "presentation",
                                  language: str = "English",
                                  num_sections: int = 5,
                                  standards: List[str] = None,
                                  custom_requirements: str = "",
                                  requested_resources: List[str] = None) -> List[Dict[str, Any]]:
        """
        Optimized single-call workflow for fast content generation
        Returns structured content compatible with handlers
        """
        
        logger.info(f"Agent Coordinator generating {resource_type} for: {lesson_topic}")
        
        # Analyze requested resources for content optimization
        if requested_resources:
            content_strategy = self._determine_content_strategy(requested_resources, resource_type)
            logger.info(f"Content strategy for {requested_resources}: {content_strategy}")
        else:
            content_strategy = "single_resource"
        
        try:
            # Get the appropriate specialist agent
            agent_key = self._normalize_resource_type(resource_type)
            specialist_agent = self.specialist_agents.get(agent_key)
            
            if not specialist_agent:
                logger.error(f"No specialist agent found for: {resource_type}")
                raise ValueError(f"Unsupported resource type: {resource_type}")
            
            # Single API call through specialist agent (includes embedded research)
            logger.info(f"Generating content with {specialist_agent.name}")
            
            # Check if this is the optimized quiz agent (different interface)
            if agent_key == "quiz":
                # Enhance requirements based on content strategy
                enhanced_requirements = self._enhance_requirements_for_strategy(
                    custom_requirements, content_strategy, requested_resources
                )
                
                structured_content = specialist_agent.create_structured_content(
                    lesson_topic=lesson_topic,
                    subject_focus=subject_focus,
                    grade_level=grade_level,
                    language=language,
                    num_sections=num_sections,
                    standards=standards,
                    custom_requirements=enhanced_requirements
                )
            else:
                # Base specialist agents - use enhanced research data based on strategy
                mock_research_data = self._create_enhanced_research_data(
                    lesson_topic, subject_focus, content_strategy, requested_resources
                )
                
                # Enhance requirements based on content strategy
                enhanced_requirements = self._enhance_requirements_for_strategy(
                    custom_requirements, content_strategy, requested_resources
                )
                
                structured_content = specialist_agent.create_structured_content(
                    research_data=mock_research_data,
                    num_sections=num_sections,
                    lesson_topic=lesson_topic,
                    subject_focus=subject_focus,
                    grade_level=grade_level,
                    language=language,
                    custom_requirements=enhanced_requirements
                )
            
            # Validate the structured content format
            if not self._validate_structured_content(structured_content):
                logger.error("Generated content does not match expected format")
                raise ValueError("Invalid structured content format")
            
            logger.info(f"Agent workflow complete: {len(structured_content)} sections generated")
            return structured_content
            
        except Exception as e:
            logger.error(f"Error in agent workflow: {e}")
            # Fallback to basic structured content
            return self._create_emergency_fallback(lesson_topic, num_sections, language)
    
    def _validate_structured_content(self, structured_content: List[Dict[str, Any]]) -> bool:
        """Validate that generated content matches the expected format"""
        if not isinstance(structured_content, list):
            return False
        
        for section in structured_content:
            if not isinstance(section, dict):
                return False
            
            # Check required fields
            required_fields = ["title", "layout", "content"]
            for field in required_fields:
                if field not in section:
                    logger.error(f"Missing required field: {field}")
                    return False
            
            # Validate content is a list
            if not isinstance(section["content"], list):
                logger.error("Content field must be a list")
                return False
        
        return True
    
    def _normalize_resource_type(self, resource_type: str) -> str:
        """Normalize resource type to agent key"""
        normalized = resource_type.lower().replace(" ", "_").replace("-", "_")
        
        if "quiz" in normalized or "test" in normalized or "assessment" in normalized:
            return "quiz"
        elif "lesson" in normalized and "plan" in normalized:
            return "lesson_plan"
        elif "worksheet" in normalized or "practice" in normalized:
            return "worksheet"
        else:
            return "presentation"  # Default
    
    def _create_emergency_fallback(self, lesson_topic: str, num_sections: int, language: str) -> List[Dict[str, Any]]:
        """Create emergency fallback content that matches the expected format"""
        logger.warning("Creating emergency fallback content")
        
        fallback_sections = []
        for i in range(num_sections):
            fallback_sections.append({
                "title": f"{lesson_topic} - Section {i+1}",
                "layout": "TITLE_AND_CONTENT",
                "content": [
                    f"Key concepts for {lesson_topic}",
                    f"Important information about this topic",
                    "Examples and applications",
                    "Student practice opportunities"
                ]
            })
        
        return fallback_sections
    
    def _determine_content_strategy(self, requested_resources: List[str], current_resource: str) -> str:
        """Determine content generation strategy based on requested resources"""
        if not requested_resources:
            return "single_resource"
        
        # Normalize resource names
        normalized_resources = [self._normalize_resource_type(r) for r in requested_resources]
        
        # If only one resource type, optimize for that
        if len(set(normalized_resources)) == 1:
            return "single_resource_optimized"
        
        # Multiple resource types - determine strategy
        has_presentation = any(r == "presentation" for r in normalized_resources)
        has_quiz = any(r == "quiz" for r in normalized_resources)
        has_worksheet = any(r == "worksheet" for r in normalized_resources)
        has_lesson_plan = any(r == "lesson_plan" for r in normalized_resources)
        
        # Common combinations
        if has_presentation and has_quiz and not has_worksheet and not has_lesson_plan:
            return "teaching_and_assessment"
        elif has_presentation and has_worksheet and not has_quiz and not has_lesson_plan:
            return "teaching_and_practice"
        elif has_quiz and has_worksheet and not has_presentation and not has_lesson_plan:
            return "assessment_and_practice"
        elif has_lesson_plan and (has_presentation or has_quiz or has_worksheet):
            return "comprehensive_lesson"
        else:
            return "multi_resource_comprehensive"
    
    def _enhance_requirements_for_strategy(self, base_requirements: str, strategy: str, 
                                         requested_resources: List[str] = None) -> str:
        """Enhance custom requirements based on content strategy"""
        
        strategy_enhancements = {
            "single_resource": "",
            "single_resource_optimized": "Focus deeply on content that works exceptionally well for this single resource type.",
            "teaching_and_assessment": """
Create content that serves dual purposes:
- Clear explanations and examples perfect for presentation teaching
- Testable concepts and measurable learning outcomes for quizzes
- Include specific facts, definitions, and procedures that can be both taught and assessed
- Balance conceptual understanding with concrete, testable knowledge
""",
            "teaching_and_practice": """
Create content that supports both instruction and hands-on practice:
- Clear step-by-step explanations suitable for presentation format
- Practice-ready problems and activities for worksheet application
- Include guided examples that can become independent practice exercises
- Focus on skills that can be demonstrated and then practiced
""",
            "assessment_and_practice": """
Create content optimized for evaluation and skill building:
- Assessment-ready concepts with clear correct answers
- Practice problems that build toward quiz-level competency
- Include both formative practice and summative assessment opportunities
- Focus on measurable skills and concrete knowledge
""",
            "comprehensive_lesson": """
Create complete instructional content that supports full lesson implementation:
- Structured learning progression from introduction to mastery
- Multiple delivery modalities (direct instruction, practice, assessment)
- Include all components needed for effective lesson delivery
- Balance conceptual understanding with practical application
""",
            "multi_resource_comprehensive": """
Create robust, versatile content that adapts well to multiple resource formats:
- Core concepts that can be taught, practiced, and assessed
- Multiple examples and applications for different contexts
- Both procedural knowledge and conceptual understanding
- Content rich enough to support various instructional approaches
"""
        }
        
        enhancement = strategy_enhancements.get(strategy, "")
        
        if enhancement:
            if base_requirements:
                return f"{base_requirements}\n\nSTRATEGIC OPTIMIZATION:\n{enhancement}"
            else:
                return f"STRATEGIC OPTIMIZATION:\n{enhancement}"
        
        return base_requirements
    
    def _create_enhanced_research_data(self, lesson_topic: str, subject_focus: str, 
                                     strategy: str, requested_resources: List[str] = None) -> Dict[str, Any]:
        """Create research data optimized for the content strategy"""
        
        base_data = {
            "core_concepts": [f"{lesson_topic} fundamentals", f"{lesson_topic} applications", f"{lesson_topic} practice"],
            "key_learning_points": [f"Understanding {lesson_topic}", f"Applying {lesson_topic}", f"Mastering {lesson_topic}"],
            "age_appropriate_examples": [f"{lesson_topic} in daily life", f"Real-world {lesson_topic}", f"Student examples"],
            "vocabulary": [{"term": "concept", "definition": f"Key idea in {lesson_topic}"}],
            "common_misconceptions": [f"Common error in {lesson_topic}"]
        }
        
        # Enhance based on strategy
        if strategy == "teaching_and_assessment":
            base_data["assessment_ready_concepts"] = [f"Testable {lesson_topic} facts", f"Measurable {lesson_topic} skills"]
            base_data["teaching_examples"] = [f"Visual {lesson_topic} demonstrations", f"Step-by-step {lesson_topic} process"]
            
        elif strategy == "teaching_and_practice":
            base_data["practice_opportunities"] = [f"Hands-on {lesson_topic} activities", f"Independent {lesson_topic} exercises"]
            base_data["guided_examples"] = [f"Scaffolded {lesson_topic} practice", f"Progressive {lesson_topic} challenges"]
            
        elif strategy == "comprehensive_lesson":
            base_data["lesson_components"] = [f"{lesson_topic} introduction", f"{lesson_topic} development", f"{lesson_topic} closure"]
            base_data["instructional_strategies"] = [f"Direct {lesson_topic} instruction", f"Collaborative {lesson_topic} learning"]
            
        elif strategy == "multi_resource_comprehensive":
            base_data["versatile_content"] = [f"Multi-modal {lesson_topic} explanations", f"Adaptable {lesson_topic} activities"]
            base_data["cross_format_examples"] = [f"Flexible {lesson_topic} scenarios", f"Transferable {lesson_topic} skills"]
        
        return base_data