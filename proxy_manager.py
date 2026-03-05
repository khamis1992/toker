"""Proxy management for TikTok bot."""
import asyncio
import aiohttp
import random
import re
from typing import List, Optional
from exceptions import TikTokProxyError


class ProxyManager:
    """Manages proxy rotation and health checking."""
    
    def __init__(self, proxy_file: str = "proxies.txt"):
        self.proxies: List[str] = []
        self.failed_proxies: set = set()
        self.proxy_file = proxy_file
        self._load_proxies()
    
    def _load_proxies(self):
        """Load proxies from file."""
        try:
            with open(self.proxy_file, 'r') as f:
                self.proxies = [line.strip() for line in f if line.strip()]
            print(f"Loaded {len(self.proxies)} proxies")
        except FileNotFoundError:
            print(f"Proxy file {self.proxy_file} not found. Running without proxies.")
            self.proxies = []
        except Exception as e:
            print(f"Error loading proxies: {e}")
            self.proxies = []
    
    def get_proxy(self) -> Optional[str]:
        """Get a healthy proxy."""
        if not self.proxies:
            return None
            
        # Filter out failed proxies
        healthy_proxies = [p for p in self.proxies if p not in self.failed_proxies]
        
        if not healthy_proxies:
            # Reset failed proxies if all are marked as failed
            print("All proxies marked as failed. Resetting failed proxy list.")
            self.failed_proxies.clear()
            healthy_proxies = self.proxies
        
        if healthy_proxies:
            return random.choice(healthy_proxies)
        return None
    
    def mark_proxy_failed(self, proxy: str):
        """Mark a proxy as failed."""
        self.failed_proxies.add(proxy)
        print(f"Marked proxy as failed: {proxy}")
    
    async def test_proxy(self, proxy: str) -> bool:
        """Test if a proxy is working."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://httpbin.org/ip",
                    proxy=proxy,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return True
        except Exception:
            pass
        return False
    
    def get_free_proxy_sources(self) -> list:
        """Return a list of free proxy sources."""
        return [
            {
                "name": "ProxyScrape",
                "url": "https://proxyscrape.com/free-proxy-list",
                "description": "Community-maintained free proxy list"
            },
            {
                "name": "HideMyAss",
                "url": "https://hidemyass.com/proxy-checker",
                "description": "Limited free tier proxy service"
            },
            {
                "name": "FreeProxyLists",
                "url": "https://free-proxy-list.net/",
                "description": "Public proxy lists updated regularly"
            }
        ]
    
    def validate_proxy_format(self, proxy: str) -> bool:
        """Validate if proxy string is in correct format."""
        # Check for common proxy formats
        patterns = [
            r'^https?://[\w\.\-]+:\d+$',  # http://proxy:port
            r'^https?://[\w\.\-]+:\d+@\w+:\w+$',  # http://user:pass@proxy:port
            r'^socks[45]://[\w\.\-]+:\d+$',  # socks proxy
        ]
        
        return any(re.match(pattern, proxy) for pattern in patterns)
    
    async def health_check(self):
        """Perform health check on all proxies."""
        if not self.proxies:
            return
            
        print("Performing proxy health check...")
        tasks = [self.test_proxy(proxy) for proxy in self.proxies[:5]]  # Limit to 5 for speed
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        working_count = sum(1 for result in results if result is True)
        print(f"Health check complete: {working_count}/{min(5, len(self.proxies))} proxies working")


# Global proxy manager instance
proxy_manager = ProxyManager()