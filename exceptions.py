"""Custom exceptions for the TikTok bot."""
import asyncio
import time
from typing import Optional


class TikTokBotError(Exception):
    """Base exception for TikTok bot errors."""
    pass


class TikTokViewerError(TikTokBotError):
    """Exception raised for viewer-related errors."""
    def __init__(self, viewer_id: int, message: str, original_exception: Optional[Exception] = None):
        self.viewer_id = viewer_id
        self.original_exception = original_exception
        super().__init__(f"Viewer {viewer_id}: {message}")


class TikTokContentNotFoundError(TikTokViewerError):
    """Exception raised when content cannot be found."""
    pass


class TikTokAntiBotError(TikTokViewerError):
    """Exception raised when TikTok detects bot activity."""
    pass


class TikTokNetworkError(TikTokViewerError):
    """Exception raised for network-related issues."""
    pass


class TikTokProxyError(TikTokNetworkError):
    """Exception raised for proxy-related issues."""
    pass


class RetryManager:
    """Manages retry logic with exponential backoff."""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
    
    async def execute_with_retry(self, func, *args, **kwargs):
        """Execute a function with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                return await func(*args, **kwargs)
            except (TikTokNetworkError, TikTokProxyError) as e:
                last_exception = e
                if attempt < self.max_attempts - 1:  # Don't sleep on last attempt
                    delay = self.base_delay * (2 ** attempt)  # Exponential backoff
                    print(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    print(f"All {self.max_attempts} attempts failed.")
                    
        raise last_exception