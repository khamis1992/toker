"""Configuration for the TikTok bot."""
import os
from dataclasses import dataclass
from typing import List


@dataclass
class BotConfig:
    # Base configuration
    live_url: str = "https://www.tiktok.com/@khamish92/live"
    num_viewers: int = 3
    headless: bool = True
    
    # Timing configuration
    page_load_timeout: int = 60000  # 60 seconds
    element_wait_timeout: int = 10000  # 10 seconds
    session_max_duration: int = 1800  # 30 minutes
    keepalive_min_interval: int = 30
    keepalive_max_interval: int = 60
    
    # Retry configuration
    max_retry_attempts: int = 3
    base_retry_delay: float = 2.0
    
    # Browser configuration
    window_width: int = 1366
    window_height: int = 768
    
    # Proxy configuration
    proxy_file: str = "proxies.txt"
    proxy_test_url: str = "http://httpbin.org/ip"
    
    # Debug configuration
    debug_screenshots: bool = True
    screenshot_dir: str = "screenshots"
    log_file: str = "tiktok_bot.log"
    log_level: str = "INFO"
    
    # Anti-detection settings
    user_agent_fallback: str = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    
    def __post_init__(self):
        # Create directories if they don't exist
        if self.debug_screenshots and not os.path.exists(self.screenshot_dir):
            os.makedirs(self.screenshot_dir)


# Global configuration instance
config = BotConfig()