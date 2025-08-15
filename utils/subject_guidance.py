"""
Subject-specific prompt optimization system
Provides targeted, concise guidance for major subject areas
"""

class SubjectSpecificPrompts:
    """Subject-specific guidance system for educational content generation"""
    
    @staticmethod
    def get_subject_guidance(subject_focus: str, resource_type: str = "worksheet") -> dict:
        """Get subject-specific guidance for content generation"""
        
        subject_lower = subject_focus.lower()
        
        # Determine primary subject area
        if any(keyword in subject_lower for keyword in ['math', 'mathematics', 'algebra', 'geometry', 'calculus', 'arithmetic']):
            return SubjectSpecificPrompts._get_math_guidance(resource_type)
        elif any(keyword in subject_lower for keyword in ['science', 'biology', 'chemistry', 'physics', 'earth science']):
            return SubjectSpecificPrompts._get_science_guidance(resource_type)
        elif any(keyword in subject_lower for keyword in ['english', 'language arts', 'literature', 'reading', 'writing']):
            return SubjectSpecificPrompts._get_english_guidance(resource_type)
        elif any(keyword in subject_lower for keyword in ['social studies', 'history', 'geography', 'civics', 'government']):
            return SubjectSpecificPrompts._get_social_studies_guidance(resource_type)
        elif any(keyword in subject_lower for keyword in ['spanish', 'french', 'german', 'chinese', 'world language']):
            return SubjectSpecificPrompts._get_world_language_guidance(resource_type)
        else:
            return SubjectSpecificPrompts._get_general_guidance(resource_type)
    
    @staticmethod
    def _get_math_guidance(resource_type: str) -> dict:
        """Math-specific guidance"""
        return {
            "key_principles": [
                "Show work and step-by-step solutions",
                "Use real-world contexts (money, measurements, sports)",
                "Include visual representations when possible",
                "Progress from concrete to abstract concepts"
            ],
            "question_types": [
                "calculation", "word_problem", "multiple_choice", "fill_blank"
            ],
            "content_requirements": [
                "Include units in answers when applicable",
                "Use grade-appropriate number ranges",
                "Provide manipulative suggestions for younger grades",
                "Show multiple solution strategies when relevant"
            ],
            "common_issues": [
                "Ensure problems have single correct answers",
                "Use realistic numbers and scenarios",
                "Check that word problems aren't overly complex linguistically"
            ],
            "example_formats": {
                "calculation": "Solve: 245 + 378 = ___",
                "word_problem": "Maria has 15 stickers. She buys 8 more packs with 6 stickers each. How many total?",
                "visual": "[Teacher: Use base-10 blocks to model this problem]"
            }
        }
    
    @staticmethod
    def _get_science_guidance(resource_type: str) -> dict:
        """Science-specific guidance"""
        return {
            "key_principles": [
                "Connect to observable phenomena",
                "Use scientific vocabulary with definitions",
                "Include cause-and-effect relationships",
                "Encourage evidence-based reasoning"
            ],
            "question_types": [
                "observation", "hypothesis", "multiple_choice", "short_answer", "diagram_analysis"
            ],
            "content_requirements": [
                "Use grade-appropriate scientific terms",
                "Include simple experiments or observations students can do",
                "Connect to everyday experiences",
                "Use metric units appropriately"
            ],
            "common_issues": [
                "Avoid concepts beyond grade-level understanding",
                "Don't require equipment students don't have",
                "Keep safety in mind for any suggested activities"
            ],
            "example_formats": {
                "observation": "What happens when you mix baking soda and vinegar?",
                "hypothesis": "If plants need sunlight, then plants in dark places will ___",
                "connection": "How is this similar to what you see in your kitchen?"
            }
        }
    
    @staticmethod
    def _get_english_guidance(resource_type: str) -> dict:
        """English Language Arts specific guidance"""
        return {
            "key_principles": [
                "ALWAYS include text excerpts - never reference external books",
                "Create age-appropriate original passages",
                "Focus on comprehension strategies",
                "Connect to students' experiences"
            ],
            "question_types": [
                "reading_comprehension", "literary_analysis", "vocabulary", "grammar", "writing_prompt"
            ],
            "content_requirements": [
                "Include 2-4 sentence excerpts for analysis questions",
                "Use diverse characters and settings",
                "Teach literary devices with examples",
                "Make text accessible to all reading levels"
            ],
            "common_issues": [
                "NEVER reference specific books without providing text",
                "Avoid cultural references that exclude students",
                "Don't assume prior reading experience"
            ],
            "example_formats": {
                "with_excerpt": "Read this passage: 'The old tree creaked in the wind...' What mood does this create?",
                "vocabulary": "In the sentence 'She was ecstatic about winning,' what does 'ecstatic' mean?",
                "analysis": "What clue tells you the character is nervous?"
            }
        }
    
    @staticmethod
    def _get_social_studies_guidance(resource_type: str) -> dict:
        """Social Studies specific guidance"""
        return {
            "key_principles": [
                "Include primary source excerpts when appropriate",
                "Connect past to present",
                "Use maps, timelines, and visual thinking tools",
                "Promote civic understanding"
            ],
            "question_types": [
                "document_analysis", "cause_effect", "compare_contrast", "multiple_choice", "short_answer"
            ],
            "content_requirements": [
                "Provide historical context within questions",
                "Use age-appropriate primary sources",
                "Include diverse perspectives",
                "Connect to current events when relevant"
            ],
            "common_issues": [
                "Avoid overwhelming students with too much historical detail",
                "Present multiple perspectives on historical events",
                "Don't assume background knowledge"
            ],
            "example_formats": {
                "primary_source": "This 1920s newspaper headline reads: '...' What does this tell us about the time period?",
                "connection": "How is this historical event similar to something happening today?",
                "geography": "Based on this map feature, why might people settle here?"
            }
        }
    
    @staticmethod
    def _get_world_language_guidance(resource_type: str) -> dict:
        """World Language specific guidance"""
        return {
            "key_principles": [
                "Start with high-frequency vocabulary",
                "Use authentic cultural contexts",
                "Practice all four skills: reading, writing, listening, speaking",
                "Make language learning meaningful and communicative"
            ],
            "question_types": [
                "vocabulary", "translation", "cultural_knowledge", "fill_blank", "multiple_choice"
            ],
            "content_requirements": [
                "Use cognates when available to support learning",
                "Include cultural context, not just language",
                "Provide English support for complex instructions",
                "Use realistic, practical scenarios"
            ],
            "common_issues": [
                "Don't overwhelm with too many new words at once",
                "Avoid stereotypical cultural representations",
                "Consider different proficiency levels within the same grade"
            ],
            "example_formats": {
                "context": "At a restaurant in Spain, you want to order pizza. What would you say?",
                "cultural": "In Mexico, this holiday celebrates... When is it celebrated?",
                "practical": "How would you ask for directions to the library?"
            }
        }
    
    @staticmethod
    def _get_general_guidance(resource_type: str) -> dict:
        """General guidance for other subjects"""
        return {
            "key_principles": [
                "Use clear, age-appropriate language",
                "Connect to student experiences",
                "Provide concrete examples",
                "Encourage critical thinking"
            ],
            "question_types": [
                "multiple_choice", "short_answer", "application", "analysis"
            ],
            "content_requirements": [
                "Include real-world connections",
                "Use varied question types",
                "Provide clear instructions",
                "Support different learning styles"
            ],
            "common_issues": [
                "Avoid overly complex language",
                "Don't assume prior knowledge",
                "Keep cultural sensitivity in mind"
            ],
            "example_formats": {
                "application": "How would you use this concept in real life?",
                "analysis": "What pattern do you notice in these examples?",
                "connection": "How does this relate to something you know?"
            }
        }

    @staticmethod
    def format_subject_guidance_for_prompt(subject_focus: str, resource_type: str = "worksheet") -> str:
        """Format subject guidance into a concise prompt section"""
        guidance = SubjectSpecificPrompts.get_subject_guidance(subject_focus, resource_type)
        
        # Create concise prompt text
        prompt_parts = []
        
        # Key principles (most important)
        principles = " • ".join(guidance["key_principles"])
        prompt_parts.append(f"SUBJECT FOCUS: {principles}")
        
        # Question types
        types = ", ".join(guidance["question_types"])
        prompt_parts.append(f"RECOMMENDED TYPES: {types}")
        
        # Most critical requirement
        if guidance["content_requirements"]:
            critical = guidance["content_requirements"][0]
            prompt_parts.append(f"CRITICAL: {critical}")
        
        return " | ".join(prompt_parts)
    
    @staticmethod
    def get_detailed_subject_guidance(subject_focus: str) -> str:
        """Get detailed subject guidance for research agents"""
        guidance = SubjectSpecificPrompts.get_subject_guidance(subject_focus, "research")
        
        # Create detailed research guidance
        research_parts = []
        
        # Key principles
        if guidance["key_principles"]:
            research_parts.append("KEY RESEARCH PRINCIPLES:")
            for principle in guidance["key_principles"]:
                research_parts.append(f"• {principle}")
            research_parts.append("")
        
        # Content requirements
        if guidance["content_requirements"]:
            research_parts.append("CONTENT REQUIREMENTS:")
            for req in guidance["content_requirements"]:
                research_parts.append(f"• {req}")
            research_parts.append("")
        
        # Common issues to avoid
        if guidance["common_issues"]:
            research_parts.append("AVOID THESE ISSUES:")
            for issue in guidance["common_issues"]:
                research_parts.append(f"• {issue}")
        
        return "\n".join(research_parts)
