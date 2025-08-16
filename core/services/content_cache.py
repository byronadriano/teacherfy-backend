# core/services/content_cache.py
import hashlib
import json
import logging
import time
from typing import Dict, List, Optional, Any
from core.database.database import get_db_connection

logger = logging.getLogger(__name__)

class ContentCacheService:
    """Production-ready service for caching and retrieving generated content"""
    
    # In-memory cache for extremely fast lookups (LRU-style)
    _memory_cache = {}
    _cache_timestamps = {}
    _max_memory_cache_size = 50  # Keep 50 most recent items in memory
    _memory_cache_ttl = 300  # 5 minutes TTL for memory cache
    
    @staticmethod
    def _sanitize_cache_input(text: str) -> str:
        """Sanitize input for safe caching - prevent PII from being cached"""
        if not text or len(text.strip()) == 0:
            return text
            
        # Convert to lowercase for normalization
        sanitized = text.lower().strip()
        
        # List of patterns that might indicate personal/sensitive information
        sensitive_patterns = [
            'student name', 'child name', 'my son', 'my daughter', 'my class',
            'school district', 'private school', 'confidential', 'personal',
            '@', 'phone', 'address', 'email', 'contact', '.com', '.edu',
            'mr.', 'mrs.', 'miss', 'teacher', 'principal', 'parent'
        ]
        
        for pattern in sensitive_patterns:
            if pattern in sanitized:
                raise ValueError(f"Potential PII detected: {pattern}")
                
        # Additional length check - very long topics might contain personal details
        if len(sanitized) > 200:
            raise ValueError("Topic too long, might contain personal information")
                
        return sanitized
    
    @staticmethod
    def _clean_memory_cache():
        """Remove expired entries and maintain size limit"""
        current_time = time.time()
        
        # Remove expired entries
        expired_keys = [
            key for key, timestamp in ContentCacheService._cache_timestamps.items()
            if current_time - timestamp > ContentCacheService._memory_cache_ttl
        ]
        
        for key in expired_keys:
            ContentCacheService._memory_cache.pop(key, None)
            ContentCacheService._cache_timestamps.pop(key, None)
        
        # Maintain size limit (remove oldest entries)
        if len(ContentCacheService._memory_cache) > ContentCacheService._max_memory_cache_size:
            sorted_keys = sorted(
                ContentCacheService._cache_timestamps.items(),
                key=lambda x: x[1]
            )
            
            keys_to_remove = [key for key, _ in sorted_keys[:-ContentCacheService._max_memory_cache_size]]
            for key in keys_to_remove:
                ContentCacheService._memory_cache.pop(key, None)
                ContentCacheService._cache_timestamps.pop(key, None)
    
    @staticmethod
    def _generate_cache_key(
        resource_type: str,
        lesson_topic: str, 
        subject_focus: str,
        grade_level: str,
        language: str = "English",
        num_sections: int = 5,
        selected_standards: Optional[List[str]] = None
    ) -> Optional[str]:
        """Generate a deterministic cache key, or None if caching should be skipped"""
        
        # Sanitize inputs to prevent PII caching
        try:
            clean_topic = ContentCacheService._sanitize_cache_input(lesson_topic)
            clean_subject = ContentCacheService._sanitize_cache_input(subject_focus)
            clean_grade = ContentCacheService._sanitize_cache_input(grade_level)
        except ValueError as e:
            logger.info(f"⚠️ Skipping cache due to sensitive content: {e}")
            return None
        
        # Normalize inputs for consistent hashing
        cache_data = {
            "resource_type": resource_type.lower().strip(),
            "lesson_topic": clean_topic,
            "subject_focus": clean_subject, 
            "grade_level": clean_grade,
            "language": language.lower().strip(),
            "num_sections": num_sections,
            "selected_standards": sorted(selected_standards or [])
        }
        
        cache_string = json.dumps(cache_data, sort_keys=True)
        cache_hash = hashlib.sha256(cache_string.encode()).hexdigest()
        
        return cache_hash
    
    @staticmethod
    def get_cached_content(
        resource_type: str,
        lesson_topic: str,
        subject_focus: str, 
        grade_level: str,
        language: str = "English",
        num_sections: int = 5,
        selected_standards: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieve cached content with optimization and PII protection"""
        
        try:
            cache_key = ContentCacheService._generate_cache_key(
                resource_type, lesson_topic, subject_focus, grade_level,
                language, num_sections, selected_standards
            )
            
            if cache_key is None:
                return None
            
            ContentCacheService._clean_memory_cache()
            
            # Check memory cache first
            if cache_key in ContentCacheService._memory_cache:
                logger.info(f"⚡ Memory cache HIT for {resource_type} '{lesson_topic}'")
                return ContentCacheService._memory_cache[cache_key]
            
            # Check database cache
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE content_cache 
                        SET last_used_at = CURRENT_TIMESTAMP,
                            generation_count = generation_count + 1
                        WHERE cache_key_hash = %s
                        RETURNING structured_content, generation_count
                    """, (cache_key,))
                    
                    result = cursor.fetchone()
                    
                    if result:
                        conn.commit()
                        structured_content, generation_count = result
                        
                        cache_response = {
                            "structured_content": structured_content,
                            "cached": True
                        }
                        
                        ContentCacheService._memory_cache[cache_key] = cache_response
                        ContentCacheService._cache_timestamps[cache_key] = time.time()
                        
                        logger.info(f"✅ DB cache HIT for {resource_type} '{lesson_topic}' (used {generation_count} times)")
                        return cache_response
                    
                    logger.info(f"🔍 Cache MISS for {resource_type} '{lesson_topic}'")
                    return None
                        
        except Exception as e:
            logger.error(f"❌ Error retrieving cached content: {e}")
            return None
    
    @staticmethod
    def cache_content(
        resource_type: str,
        lesson_topic: str,
        subject_focus: str,
        grade_level: str,
        structured_content: List[Dict[str, Any]],
        language: str = "English",
        num_sections: int = 5,
        selected_standards: Optional[List[str]] = None,
        user_id: Optional[int] = None
    ) -> bool:
        """Cache generated content with PII protection"""
        
        try:
            cache_key = ContentCacheService._generate_cache_key(
                resource_type, lesson_topic, subject_focus, grade_level,
                language, num_sections, selected_standards
            )
            
            if cache_key is None:
                logger.info(f"⚠️ Skipping cache storage due to sensitive content")
                return False
            
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO content_cache (
                            resource_type, lesson_topic, subject_focus, grade_level,
                            language, num_sections, selected_standards, cache_key_hash,
                            structured_content, generation_count, created_by_user_id
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (cache_key_hash) DO UPDATE SET
                            structured_content = EXCLUDED.structured_content,
                            last_used_at = CURRENT_TIMESTAMP
                    """, (
                        resource_type, lesson_topic, subject_focus, grade_level,
                        language, num_sections, selected_standards, cache_key,
                        json.dumps(structured_content), 1, user_id
                    ))
                    
                    conn.commit()
                    
                    # Invalidate memory cache
                    if cache_key in ContentCacheService._memory_cache:
                        del ContentCacheService._memory_cache[cache_key]
                        ContentCacheService._cache_timestamps.pop(cache_key, None)
                    
                    logger.info(f"💾 Cached content for {resource_type} '{lesson_topic}'")
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Error caching content: {e}")
            return False
    
    @staticmethod
    def get_cache_stats() -> Dict[str, Any]:
        """Get cache statistics"""
        
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as total_entries,
                            SUM(generation_count) as total_cache_hits,
                            AVG(generation_count) as avg_hits_per_entry,
                            COUNT(DISTINCT resource_type) as resource_types_cached
                        FROM content_cache
                    """)
                    
                    result = cursor.fetchone()
                    if result:
                        return {
                            "total_entries": result[0],
                            "total_cache_hits": result[1] or 0,
                            "avg_hits_per_entry": float(result[2]) if result[2] else 0.0,
                            "resource_types_cached": result[3],
                            "memory_cache_size": len(ContentCacheService._memory_cache)
                        }
                    return {}
                    
        except Exception as e:
            logger.error(f"❌ Error getting cache stats: {e}")
            return {}