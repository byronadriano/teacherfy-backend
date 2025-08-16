"""
Agent Coordinator - Optimized single-call approach for fast educational content generation
"""

from typing import Dict, List, Any
from config.settings import logger
from .specialists.quiz_generator import OptimizedQuizAgent
from .specialists.worksheet_generator import OptimizedWorksheetAgent
from .specialists.lesson_plan import OptimizedLessonPlanAgent
from .specialists.presentation import PresentationSpecialistAgent
from .specialists.content_research import ContentResearchAgent

class AgentCoordinator:
    """Optimized coordinator using single API calls for faster response times"""
    
    def __init__(self):
        self.specialist_agents = {
            "presentation": PresentationSpecialistAgent(),
            "quiz": OptimizedQuizAgent(),  # Optimized single-call quiz generation
            "worksheet": OptimizedWorksheetAgent(),  # Optimized single-call worksheet generation
            "lesson_plan": OptimizedLessonPlanAgent()  # Optimized single-call lesson plan generation
        }
        self.research_agent = ContentResearchAgent()  # For multi-resource alignment
        self._generated_content = {}  # Store generated content for cross-resource alignment
        logger.info("Agent Coordinator initialized with optimized single-call agents and research agent")
    
    def generate_multiple_resources(self,
                                   lesson_topic: str,
                                   subject_focus: str,
                                   grade_level: str,
                                   language: str,
                                   resource_types: List[str],
                                   standards: List[str] = None,
                                   custom_requirements: str = "",
                                   **kwargs) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate multiple resources with proper alignment using shared research.
        Uses ContentResearchAgent for consistent foundation across all resources.
        """
        logger.info(f"Generating multiple aligned resources: {resource_types}")
        
        # STEP 1: Generate shared research for alignment
        logger.info("🔍 Generating shared research for content alignment...")
        shared_research = self.research_agent.research_topic(
            lesson_topic=lesson_topic,
            subject_focus=subject_focus,
            grade_level=grade_level,
            language=language,
            standards=standards,
            custom_requirements=custom_requirements
        )
        logger.info("✅ Shared research complete - all resources will use consistent foundation")
        
        results = {}
        
        # STEP 2: Generate non-lesson-plan resources using shared research
        other_resources = [rt for rt in resource_types if rt != 'lesson_plan' and rt != 'lesson plan']
        
        for resource_type in other_resources:
            logger.info(f"Generating {resource_type} with shared research foundation...")
            results[resource_type] = self.generate_structured_content(
                lesson_topic=lesson_topic,
                subject_focus=subject_focus,
                grade_level=grade_level,
                resource_type=resource_type,
                language=language,
                standards=standards,
                custom_requirements=custom_requirements,
                requested_resources=resource_types,  # Pass all requested resources for strategy
                shared_research_data=shared_research,  # Pass shared research
                **kwargs
            )
        
        # STEP 3: Generate lesson plan LAST with both shared research AND reference to other resources
        if 'lesson_plan' in resource_types or 'lesson plan' in resource_types:
            logger.info("Generating lesson plan with shared research + reference to other resources...")
            
            # Build reference content summary for lesson plan
            reference_summary = self._build_reference_summary(results)
            
            results['lesson_plan'] = self.generate_structured_content(
                lesson_topic=lesson_topic,
                subject_focus=subject_focus,
                grade_level=grade_level,
                resource_type='lesson_plan',
                language=language,
                standards=standards,
                custom_requirements=custom_requirements + f"\n\nREFERENCE CONTENT:\n{reference_summary}",
                requested_resources=list(results.keys()),
                shared_research_data=shared_research,  # Pass shared research
                **kwargs
            )
        
        logger.info(f"Generated {len(results)} aligned resources using shared research foundation")
        return results
    
    def _build_reference_summary(self, generated_resources: Dict) -> str:
        """Build a summary of generated resources for lesson plan reference"""
        summary_parts = []
        
        for resource_type, content in generated_resources.items():
            if resource_type == 'presentation':
                slide_titles = []
                for i, section in enumerate(content, 1):
                    title = section.get('title', f'Slide {i}')
                    slide_titles.append(f"Slide {i}: {title}")
                
                summary_parts.append(f"PRESENTATION ({len(content)} slides):")
                summary_parts.extend([f"  - {title}" for title in slide_titles])
                
            elif resource_type == 'quiz':
                summary_parts.append(f"QUIZ ({len(content)} sections):")
                for section in content:
                    title = section.get('title', 'Quiz Section')
                    questions = section.get('structured_questions', [])
                    question_types = [q.get('type', 'question') for q in questions]
                    summary_parts.append(f"  - {title}: {len(questions)} questions ({', '.join(set(question_types))})")
                    
            elif resource_type == 'worksheet':
                summary_parts.append(f"WORKSHEET ({len(content)} sections):")
                for section in content:
                    title = section.get('title', 'Worksheet Section')
                    questions = section.get('structured_questions', [])
                    summary_parts.append(f"  - {title}: {len(questions)} practice problems")
        
        return "\n".join(summary_parts)
    
    def generate_structured_content(self,
                                  lesson_topic: str,
                                  subject_focus: str,
                                  grade_level: str,
                                  resource_type: str = "presentation",
                                  language: str = "English",
                                  num_sections: int = 5,
                                  standards: List[str] = None,
                                  custom_requirements: str = "",
                                  requested_resources: List[str] = None,
                                  shared_research_data: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Optimized workflow: Uses shared research when available, single-call for individual resources
        Returns structured content compatible with handlers
        """
        
        logger.info(f"Agent Coordinator generating {resource_type} for: {lesson_topic}")
        
        # Determine if we're using shared research or individual optimization
        using_shared_research = shared_research_data is not None
        if using_shared_research:
            logger.info("📚 Using shared research data for content alignment")
        
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
            
            logger.info(f"Generating content with {specialist_agent.name}")
            
            # Check if this is an optimized agent (different interface)
            if agent_key in ["quiz", "worksheet", "lesson_plan"]:
                # Enhance requirements based on content strategy
                enhanced_requirements = self._enhance_requirements_for_strategy(
                    custom_requirements, content_strategy, requested_resources
                )
                
                # Special handling for standalone lesson plans - they need research content
                if agent_key == "lesson_plan" and not using_shared_research:
                    # Check if lesson plan is the only resource being generated
                    is_standalone_lesson_plan = (
                        not requested_resources or 
                        len(requested_resources) == 1 and "lesson" in str(requested_resources[0]).lower()
                    )
                    
                    if is_standalone_lesson_plan:
                        logger.info("🔍 Generating research content for standalone lesson plan...")
                        research_data = self.research_agent.research_topic(
                            lesson_topic=lesson_topic,
                            subject_focus=subject_focus,
                            grade_level=grade_level,
                            language=language,
                            standards=standards,
                            custom_requirements=custom_requirements
                        )
                        
                        if research_data:
                            research_context = self._format_research_for_agents(research_data)
                            enhanced_requirements = f"{enhanced_requirements}\n\nRESEARCH FOUNDATION:\n{research_context}"
                            logger.info("✅ Research content added to standalone lesson plan generation")
                        else:
                            logger.warning("❌ Failed to generate research content for standalone lesson plan")
                
                # Add shared research context if available (for multi-resource generation)
                elif using_shared_research:
                    research_context = self._format_research_for_agents(shared_research_data)
                    enhanced_requirements = f"{enhanced_requirements}\n\nSHARED RESEARCH FOUNDATION:\n{research_context}"
                
                # For lesson plan, pass requested_resources for integration
                if agent_key == "lesson_plan":
                    structured_content = specialist_agent.create_structured_content(
                        lesson_topic=lesson_topic,
                        subject_focus=subject_focus,
                        grade_level=grade_level,
                        language=language,
                        num_sections=num_sections,
                        standards=standards,
                        custom_requirements=enhanced_requirements,
                        requested_resources=requested_resources,
                        reference_content=getattr(self, '_generated_content', {})
                    )
                else:
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
                # Base specialist agents (presentation) - use shared or enhanced research
                if using_shared_research:
                    research_data = shared_research_data
                    logger.info("Using shared research for presentation agent")
                else:
                    research_data = self._create_enhanced_research_data(
                        lesson_topic, subject_focus, content_strategy, requested_resources
                    )
                    logger.info("Using enhanced mock research for presentation agent")
                
                # Enhance requirements based on content strategy
                enhanced_requirements = self._enhance_requirements_for_strategy(
                    custom_requirements, content_strategy, requested_resources
                )
                
                structured_content = specialist_agent.create_structured_content(
                    research_data=research_data,
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
            
            # Store generated content for cross-resource alignment
            self._generated_content[resource_type] = structured_content
            
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
            
            # Check required fields - title and layout are always required
            if "title" not in section:
                logger.error("Missing required field: title")
                return False
            
            if "layout" not in section:
                logger.error("Missing required field: layout")
                return False
            
            # For new structured format, check for structured data
            has_structured_data = (
                "structured_questions" in section or 
                "structured_activities" in section or
                "content" in section
            )
            
            if not has_structured_data:
                logger.error("Section must have either structured_questions, structured_activities, or content")
                return False
            
            # If content exists, validate it's a list
            if "content" in section and not isinstance(section["content"], list):
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
    
    def _format_research_for_agents(self, research_data: Dict[str, Any]) -> str:
        """Format comprehensive research data for optimized agents that use prompts instead of structured data"""
        if not research_data:
            return ""
        
        formatted_parts = []
        
        # Core content information
        if "core_concepts" in research_data:
            concepts = research_data["core_concepts"]
            if isinstance(concepts, list):
                formatted_parts.append(f"CORE CONCEPTS: {', '.join(concepts)}")
        
        if "key_learning_points" in research_data:
            points = research_data["key_learning_points"]
            if isinstance(points, list):
                formatted_parts.append(f"KEY LEARNING POINTS: {', '.join(points)}")
        
        # Examples and applications
        if "age_appropriate_examples" in research_data:
            examples = research_data["age_appropriate_examples"]
            if isinstance(examples, list):
                formatted_parts.append(f"EXAMPLES: {', '.join(examples)}")
        
        if "real_world_connections" in research_data:
            connections = research_data["real_world_connections"]
            if isinstance(connections, list):
                formatted_parts.append(f"REAL-WORLD CONNECTIONS: {', '.join(connections)}")
        
        # Vocabulary and terminology
        if "vocabulary" in research_data:
            vocab = research_data["vocabulary"]
            if isinstance(vocab, list):
                vocab_terms = []
                for term in vocab:
                    if isinstance(term, dict) and "term" in term and "definition" in term:
                        vocab_terms.append(f"{term['term']}: {term['definition']}")
                if vocab_terms:
                    formatted_parts.append(f"KEY VOCABULARY: {'; '.join(vocab_terms)}")
        
        # Learning challenges and support
        if "common_misconceptions" in research_data:
            misconceptions = research_data["common_misconceptions"]
            if isinstance(misconceptions, list):
                formatted_parts.append(f"AVOID MISCONCEPTIONS: {', '.join(misconceptions)}")
        
        if "prerequisite_knowledge" in research_data:
            prereqs = research_data["prerequisite_knowledge"]
            if isinstance(prereqs, list):
                formatted_parts.append(f"PREREQUISITE KNOWLEDGE: {', '.join(prereqs)}")
        
        # Assessment and differentiation
        if "assessment_strategies" in research_data:
            assessment = research_data["assessment_strategies"]
            if isinstance(assessment, list):
                formatted_parts.append(f"ASSESSMENT APPROACHES: {', '.join(assessment)}")
        
        if "differentiation_strategies" in research_data:
            diff = research_data["differentiation_strategies"]
            if isinstance(diff, list):
                formatted_parts.append(f"DIFFERENTIATION: {', '.join(diff)}")
        
        return "\n".join(formatted_parts)