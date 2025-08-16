# core/services/__init__.py
"""Services module for external API integrations"""

try:
    from .unsplash_service import unsplash_service
except ImportError as e:
    print(f"Warning: Could not import unsplash_service: {e}")
    unsplash_service = None

__all__ = ['unsplash_service']