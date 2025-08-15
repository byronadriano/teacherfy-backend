# src/services/unsplash_service.py
import os
import requests
import logging
from typing import Optional, Dict, Any
from urllib.parse import quote

logger = logging.getLogger(__name__)

class UnsplashService:
    """Service for fetching images from Unsplash API"""
    
    def __init__(self):
        self.access_key = os.environ.get('UNSPLASH_ACCESS_KEY')
        self.base_url = "https://api.unsplash.com"
        
        if not self.access_key:
            logger.warning("UNSPLASH_ACCESS_KEY not found in environment variables")
    
    def search_photo(self, query: str, orientation: str = "landscape") -> Optional[Dict[str, Any]]:
        """
        Search for a photo on Unsplash based on query.
        
        Args:
            query: Search term (e.g., "mathematics", "science", "reading")
            orientation: "landscape", "portrait", or "squarish"
            
        Returns:
            Dictionary with photo data or None if not found
        """
        if not self.access_key:
            logger.error("Cannot search photos: Unsplash access key not configured")
            return None
            
        try:
            # Clean and encode the search query
            clean_query = self._clean_search_query(query)
            encoded_query = quote(clean_query)
            
            url = f"{self.base_url}/search/photos"
            params = {
                'query': clean_query,
                'orientation': orientation,
                'per_page': 1,  # We only need the first result
                'order_by': 'relevant',
                'content_filter': 'high'  # Family-friendly content
            }
            
            headers = {
                'Authorization': f'Client-ID {self.access_key}',
                'Accept-Version': 'v1'
            }
            
            logger.info(f"Searching Unsplash for: '{clean_query}' (orientation: {orientation})")
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('results') and len(data['results']) > 0:
                photo = data['results'][0]
                logger.info(f"Found photo by {photo['user']['name']} for query '{clean_query}'")
                
                return {
                    'id': photo['id'],
                    'url_regular': photo['urls']['regular'],
                    'url_small': photo['urls']['small'],
                    'url_thumb': photo['urls']['thumb'],
                    'download_url': photo['links']['download_location'],
                    'photographer_name': photo['user']['name'],
                    'photographer_username': photo['user']['username'],
                    'photographer_url': photo['user']['links']['html'],
                    'unsplash_url': photo['links']['html'],
                    'description': photo.get('description') or photo.get('alt_description', ''),
                    'width': photo['width'],
                    'height': photo['height']
                }
            else:
                logger.warning(f"No photos found for query: '{clean_query}'")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Unsplash API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error searching Unsplash photos: {e}")
            return None
    
    def download_photo(self, photo_data: Dict[str, Any]) -> Optional[bytes]:
        """
        Download photo content and trigger Unsplash download tracking.
        
        Args:
            photo_data: Photo data from search_photo()
            
        Returns:
            Image bytes or None if download failed
        """
        if not self.access_key:
            logger.error("Cannot download photo: Unsplash access key not configured")
            return None
            
        try:
            # First, trigger the download endpoint for Unsplash analytics
            self._trigger_download(photo_data['download_url'])
            
            # Then download the actual image
            image_url = photo_data['url_regular']  # Use regular size for good quality
            logger.info(f"Downloading image from: {image_url}")
            
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            logger.info(f"Successfully downloaded image ({len(response.content)} bytes)")
            return response.content
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download image: {e}")
            return None
        except Exception as e:
            logger.error(f"Error downloading photo: {e}")
            return None
    
    def _trigger_download(self, download_url: str) -> None:
        """
        Trigger Unsplash download endpoint for analytics.
        This is required by Unsplash API terms.
        """
        try:
            headers = {
                'Authorization': f'Client-ID {self.access_key}',
                'Accept-Version': 'v1'
            }
            
            response = requests.get(download_url, headers=headers, timeout=10)
            response.raise_for_status()
            logger.debug("Unsplash download event triggered successfully")
            
        except Exception as e:
            logger.warning(f"Failed to trigger Unsplash download event: {e}")
            # Don't fail the whole process if analytics tracking fails
    
    def _clean_search_query(self, query: str) -> str:
        """
        Clean and optimize search query for better Unsplash results.
        Removes duplicates and ensures proper formatting.
        
        Args:
            query: Raw search query
            
        Returns:
            Cleaned query optimized for educational content
        """
        if not query:
            return "education"
        
        # Convert to lowercase for processing
        clean_query = query.lower().strip()
        
        # Split into words and remove duplicates while preserving order
        words = clean_query.split()
        seen = set()
        unique_words = []
        
        for word in words:
            if word not in seen:
                seen.add(word)
                unique_words.append(word)
        
        # Rejoin unique words
        clean_query = ' '.join(unique_words)
        
        # Map educational terms to better search terms (avoiding duplicates)
        educational_mappings = {
            # Subjects
            'math mathematics': 'mathematics education',
            'mathematics classroom': 'mathematics education classroom',
            'science classroom': 'science education classroom',
            'reading classroom': 'reading education classroom',
            'history classroom': 'history education classroom',
            
            # Remove redundant combinations
            'classroom education classroom': 'classroom education',
            'education classroom education': 'classroom education',
            'mathematics classroom education classroomematics': 'mathematics education classroom',
        }
        
        # Apply mappings to clean up redundant terms
        for redundant, clean in educational_mappings.items():
            if redundant in clean_query:
                clean_query = clean_query.replace(redundant, clean)
        
        # Remove common words that don't help with image search
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = clean_query.split()
        filtered_words = [word for word in words if word not in stop_words]
        
        # If we filtered out everything, use the original
        if not filtered_words:
            return query
        
        result = ' '.join(filtered_words)
        
        # Ensure we have educational context without duplication
        if 'education' not in result and 'classroom' not in result and 'learning' not in result:
            result += ' education'
        
        # Final cleanup - remove any remaining duplicates
        final_words = result.split()
        seen = set()
        final_unique_words = []
        
        for word in final_words:
            if word not in seen:
                seen.add(word)
                final_unique_words.append(word)
        
        result = ' '.join(final_unique_words)
        
        logger.debug(f"Cleaned search query: '{query}' -> '{result}'")
        return result

    def generate_attribution(self, photo_data: Dict[str, Any]) -> str:
        """
        Generate proper attribution text for Unsplash photo.
        This is required by Unsplash API terms.
        
        Args:
            photo_data: Photo data from search_photo()
            
        Returns:
            Attribution string
        """
        photographer_name = photo_data['photographer_name']
        return f"Photo by {photographer_name} on Unsplash"

    def get_relevant_image(self, query: str, orientation: str = "landscape") -> Optional[str]:
        """
        Convenience wrapper that returns a direct image URL for a query.
        Kept for backward compatibility with other modules (e.g. slide_processor)
        which expect a single-image URL string via `get_relevant_image`.

        Returns the 'regular' sized image URL or None if not found.
        """
        try:
            photo = self.search_photo(query, orientation=orientation)
            if not photo:
                return None
            # Prefer the regular-sized url for good quality; fall back to small/thumb
            return photo.get('url_regular') or photo.get('url_small') or photo.get('url_thumb')
        except Exception as e:
            logger.error(f"Error in get_relevant_image: {e}")
            return None


# Create a global instance that can be imported
try:
    unsplash_service = UnsplashService()
    logger.info("Unsplash service initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Unsplash service: {e}")
    unsplash_service = None