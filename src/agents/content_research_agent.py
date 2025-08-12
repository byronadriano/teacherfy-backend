"""
Content Research Agent - Gathers comprehensive topic information
Provides foundational content that specialist agents can adapt for their specific resource types
"""

import json
from typing import Dict, List, Any, Optional
from src.config import logger, client

class ContentResearchAgent:
    """Agent responsible for researching and gathering comprehensive topic information"""
    
    def __init__(self):
        self.name = "Content Research Agent"
        
    def research_topic(self, 
                      lesson_topic: str,
                      subject_focus: str,
                      grade_level: str,
                      language: str = "English",
                      standards: List[str] = None,
                      custom_requirements: str = "") -> Dict[str, Any]:
        """
        Research comprehensive information about a topic
        Returns structured data that can be used by specialist agents
        """
        logger.info(f"Content Research Agent researching: {lesson_topic}")
        
        # Build research prompt
        standards_text = f"Standards: {', '.join(standards)}" if standards else "General learning objectives"
        
        system_prompt = f"""You are an expert educational content researcher with deep knowledge across all academic subjects. Your job is to gather comprehensive, accurate information about any topic that will be used by specialist agents to create presentations, quizzes, worksheets, and lesson plans.

CRITICAL: You must respond with VALID JSON ONLY. No additional text before or after.

Research the topic thoroughly and provide complete foundational content that works across all subjects (Math, Science, Language Arts, Social Studies, Physical Education, Music, Art, etc.) and all grade levels:

COMPREHENSIVE RESEARCH REQUIREMENTS:
1. Core concepts and essential knowledge
2. Age-appropriate explanations and real-world examples
3. Key vocabulary and terminology students need
4. Common misconceptions and learning difficulties
5. Real-world applications and connections
6. Assessment strategies and learning objectives
7. Prerequisite knowledge and skills
8. Extension opportunities for advanced learners
9. Differentiation strategies for diverse learners
10. Practical activities and engagement strategies

Respond with this exact JSON structure:
{{
  "topic_overview": "Brief overview of the topic appropriate for the grade level",
  "core_concepts": ["Essential concept 1", "Essential concept 2", "Essential concept 3"],
  "key_learning_points": ["What students should know", "What students should understand", "What students should be able to do"],
  "age_appropriate_examples": ["Concrete example 1", "Real-world example 2", "Student-relatable example 3"],
  "vocabulary": [{{"term": "key term", "definition": "clear definition", "importance": "why students need this term"}}, {{"term": "another term", "definition": "simple definition", "importance": "relevance to topic"}}],
  "common_misconceptions": ["Common error students make", "Typical misunderstanding"],
  "real_world_connections": ["How this applies to daily life", "Career connections", "Current events connections"],
  "prerequisite_knowledge": ["What students should already know", "Foundational skills needed"],
  "learning_objectives": ["Students will be able to...", "Students will understand..."],
  "assessment_strategies": ["Formative assessment idea", "Summative assessment approach"],
  "differentiation_strategies": ["Support for struggling learners", "Challenge for advanced learners", "Multiple learning styles accommodation"],
  "extension_activities": ["Enrichment opportunity", "Cross-curricular connection", "Project-based extension"],
  "teaching_tips": ["Effective instructional strategy", "Common teaching challenge solution", "Engagement technique"]
}}

Language: All content must be in {language}
Grade Level: {grade_level}
Subject: {subject_focus}"""

        user_prompt = f"""Research this educational topic thoroughly:

Topic: {lesson_topic}
Subject: {subject_focus} 
Grade Level: {grade_level}
Language: {language}
{standards_text}

Additional Requirements: {custom_requirements}

Provide comprehensive research data that specialist agents can use to create presentations, quizzes, worksheets, and lesson plans."""

        try:
            # Make API call to DeepSeek
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=3000,
                temperature=0.3,  # Lower temperature for more factual content
                stream=False
            )
            
            content = response.choices[0].message.content.strip()
            logger.debug(f"Raw research response: {content[:200]}...")
            
            # Clean and parse JSON
            try:
                # Try to extract JSON from the response
                if content.startswith('```json'):
                    content = content.split('```json')[1].split('```')[0].strip()
                elif content.startswith('```'):
                    content = content.split('```')[1].split('```')[0].strip()
                
                research_data = json.loads(content)
                logger.info(f"Successfully researched topic: {lesson_topic}")
                return research_data
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse research JSON: {e}")
                logger.error(f"Raw content: {content}")
                
                # Fallback to basic structure
                return self._create_fallback_research(lesson_topic, subject_focus, grade_level, language)
                
        except Exception as e:
            logger.error(f"Error in content research: {e}")
            return self._create_fallback_research(lesson_topic, subject_focus, grade_level, language)
    
    def _create_fallback_research(self, topic: str, subject: str, grade: str, language: str) -> Dict[str, Any]:
        """Create fallback research data when API fails"""
        logger.warning("Using fallback research data")
        
        return {
            "topic_overview": f"Educational content about {topic} for {grade} {subject}",
            "core_concepts": [
                f"Fundamental concepts of {topic}",
                f"Key principles in {subject}",
                f"Practical applications of {topic}"
            ],
            "key_learning_points": [
                f"Students will understand {topic}",
                f"Students will apply {subject} knowledge",
                "Students will make real-world connections"
            ],
            "age_appropriate_examples": [
                f"Examples related to {topic}",
                f"Real-world {subject} applications",
                "Student-relatable scenarios"
            ],
            "vocabulary": [
                {"term": "Key Term 1", "definition": f"Important concept in {topic}", "importance": f"Essential for understanding {subject}"},
                {"term": "Key Term 2", "definition": f"Essential {subject} vocabulary", "importance": f"Used throughout {topic} discussions"}
            ],
            "common_misconceptions": [
                f"Common errors in understanding {topic}",
                f"Typical {subject} misconceptions"
            ],
            "real_world_connections": [
                f"How {topic} applies to daily life",
                f"{subject} in careers and current events"
            ],
            "prerequisite_knowledge": [
                f"Basic {subject} understanding",
                "Foundational concepts students should know"
            ],
            "learning_objectives": [
                f"Students will be able to explain {topic}",
                f"Students will understand key {subject} concepts"
            ],
            "assessment_strategies": [
                "Formative assessment opportunities",
                "Summative evaluation methods"
            ],
            "differentiation_strategies": [
                "Support for struggling learners",
                "Challenge opportunities for advanced students",
                "Multiple learning styles accommodation"
            ],
            "extension_activities": [
                f"Advanced {topic} exploration",
                f"Cross-curricular {subject} projects"
            ],
            "teaching_tips": [
                f"Effective strategies for teaching {topic}",
                f"Common challenges when teaching {subject}",
                "Student engagement techniques"
            ]
        }