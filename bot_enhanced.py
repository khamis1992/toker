"""Enhanced TikTok Viewer Bot with improved stability and error handling."""
import asyncio
import random
import os
import time
import logging
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from fake_useragent import UserAgent
from exceptions import TikTokViewerError, TikTokContentNotFoundError, TikTokNetworkError, TikTokProxyError, RetryManager
from proxy_manager import proxy_manager
from config import config
from interactive_controller import InteractiveController


# Set up logging based on config
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TikTokViewer:
    def __init__(self, viewer_id: int, proxy: str = None):
        self.viewer_id = viewer_id
        self.proxy = proxy
        self.ua = UserAgent(fallback=config.user_agent_fallback)
        self.retry_manager = RetryManager(max_attempts=config.max_retry_attempts, base_delay=config.base_retry_delay)
        self.start_time = time.time()
        self.interactive_controller = InteractiveController(viewer_id)
        
    async def start(self, live_url: str):
        """Start the viewer session with enhanced error handling."""
        logger.info(f"Viewer {self.viewer_id}: Starting session")
        
        # Run session once without automatic retries
        try:
            await self._run_session(live_url)
            return True
        except Exception as e:
            logger.error(f"Viewer {self.viewer_id}: Session failed: {e}")
            return False
    
    async def _run_session(self, live_url: str):
        """Internal method to run the viewer session."""
        browser = None
        context = None
        page = None
        
        try:
            async with async_playwright() as p:
                args = [
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--window-size=1366,768',
                    '--disable-http2',
                    '--disable-blink-features=AutomationControlled'
                ]
                
                launch_options = {
                    'headless': True,
                    'args': args
                }
                
                if self.proxy:
                    proxy_url = self.proxy.strip()
                    if not proxy_url.startswith(('http://', 'https://')):
                        parts = proxy_url.split(':')
                        if len(parts) == 4:
                            proxy_url = f"http://{parts[0]}:{parts[1]}@{parts[2]}:{parts[3]}"
                    launch_options['proxy'] = {'server': proxy_url}
                    logger.info(f"Viewer {self.viewer_id}: Using proxy {proxy_url}")
                
                logger.info(f"Viewer {self.viewer_id}: Starting browser...")
                browser = await p.chromium.launch(**launch_options)
                
                context = await browser.new_context(
                    viewport={'width': config.window_width, 'height': config.window_height},
                    user_agent=self.ua.random,
                    locale='en-US',
                    timezone_id='America/New_York',
                    color_scheme='light'
                )
                
                # Enhanced automation masking
                await context.add_init_script("""
                    // Enhanced navigator masking
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                    window.chrome = { runtime: {} };
                    Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
                    
                    // Additional masking
                    window.outerWidth = window.innerWidth;
                    window.outerHeight = window.innerHeight;
                """)
                
                page = await context.new_page()
                
                # More sophisticated content blocking
                await page.route("**/*", self._should_load_resource)
                
                logger.info(f"Viewer {self.viewer_id}: Loading page...")
                
                # Go to page with better error handling
                # Use 'domcontentloaded' instead of 'load' — TikTok live pages never
                # fully fire the 'load' event due to continuous streaming resources.
                try:
                    response = await page.goto(
                        live_url,
                        wait_until='domcontentloaded',
                        timeout=config.page_load_timeout
                    )
                    logger.info(f"Viewer {self.viewer_id}: Page loaded (status: {response.status if response else 'unknown'})")
                except PlaywrightTimeout as e:
                    raise TikTokNetworkError(self.viewer_id, f"Timeout loading page: {e}")
                except Exception as e:
                    raise TikTokNetworkError(self.viewer_id, f"Failed to load page: {e}")

                # Wait for TikTok React app to render the live player
                await asyncio.sleep(8)

                # Check page content for common failure conditions before looking for video
                html = await page.content()
                html_lower = html.lower()
                if 'this account is private' in html_lower:
                    raise TikTokViewerError(self.viewer_id, "Account is private")
                if 'live has ended' in html_lower or 'this live has ended' in html_lower:
                    raise TikTokViewerError(self.viewer_id, "Live stream has ended")
                if 'isn\'t live' in html_lower or 'not live' in html_lower:
                    raise TikTokViewerError(self.viewer_id, "Stream is not currently live")

                # Try to find video with enhanced selectors and error handling
                video_found = await self._find_video_element(page)

                if not video_found:
                    # Take screenshot to see what's there
                    if config.debug_screenshots:
                        screenshot_path = f"{config.screenshot_dir}/debug_viewer_{self.viewer_id}_{int(time.time())}.png"
                        await page.screenshot(path=screenshot_path, full_page=True)
                        logger.warning(f"Viewer {self.viewer_id}: No video found. Screenshot saved: {screenshot_path}")
                    else:
                        logger.warning(f"Viewer {self.viewer_id}: No video found. Debug screenshots disabled.")

                    # Analyse page content for a more specific error message
                    if 'login' in html_lower or 'sign in' in html_lower:
                        raise TikTokViewerError(self.viewer_id, "TikTok requires login to view this stream")
                    elif 'age' in html_lower and 'restriction' in html_lower:
                        raise TikTokViewerError(self.viewer_id, "Age restriction detected")
                    elif 'not available' in html_lower or 'unavailable' in html_lower:
                        raise TikTokViewerError(self.viewer_id, "Stream not available in this region")
                    elif len(html) < 5000:
                        raise TikTokViewerError(self.viewer_id, "Page did not render properly (proxy may be blocking TikTok)")
                    else:
                        raise TikTokContentNotFoundError(self.viewer_id, "Live player not found — stream may be offline")
                
                logger.info(f"Viewer {self.viewer_id}: ✅ WATCHING")
                
                # Enhanced keep alive with session monitoring
                await self._keep_alive(page)
                
        except TikTokViewerError:
            # Re-raise specific TikTok errors
            raise
        except PlaywrightTimeout as e:
            raise TikTokNetworkError(self.viewer_id, f"Playwright timeout: {e}", e)
        except Exception as e:
            raise TikTokViewerError(self.viewer_id, f"Unexpected error: {e}", e)
        finally:
            # Proper cleanup
            if browser:
                try:
                    await browser.close()
                    logger.info(f"Viewer {self.viewer_id}: Browser closed")
                except Exception as e:
                    logger.warning(f"Viewer {self.viewer_id}: Error closing browser: {e}")
    
    async def _should_load_resource(self, route):
        """Decide whether to load a resource."""
        url = route.request.url.lower()
        resource_type = route.request.resource_type

        # Block only heavy non-essential media (ads, tracking pixels, analytics)
        BLOCKED_DOMAINS = [
            'doubleclick.net', 'googlesyndication.com', 'google-analytics.com',
            'googletagmanager.com', 'facebook.com/tr', 'amplitude.com',
            'mixpanel.com', 'hotjar.com', 'clarity.ms',
        ]
        if any(domain in url for domain in BLOCKED_DOMAINS):
            await route.abort()
            return

        # Block only image/font resources from non-TikTok domains to save bandwidth
        TIKTOK_DOMAINS = [
            'tiktok.com', 'tiktokcdn.com', 'tiktokv.com', 'ttlive.com',
            'muscdn.com', 'bytedance.com', 'byteimg.com', 'sgsnssdk.com',
            'ibytedtos.com', 'ibyteimg.com', 'pstatp.com', 'snssdk.com',
            'bdstatic.com', 'byteoversea.com', 'packetstream.io',
        ]
        is_tiktok = any(domain in url for domain in TIKTOK_DOMAINS)

        if not is_tiktok and resource_type in ['image', 'font', 'media']:
            await route.abort()
            return

        # Allow everything else (scripts, stylesheets, XHR, fetch, websocket, etc.)
        await route.continue_()
    
    async def _find_video_element(self, page):
        """Try to find video element with enhanced detection."""
        selectors = [
            'video[data-preload="auto"]',  # TikTok specific
            'video[class*="player"]',      # Player videos
            'video',                       # Standard video
            'canvas',                      # TikTok sometimes uses canvas
            '[data-e2e="live-content"]',   # Live container
            '.tiktok-web-player',          # Player container
            '[class*="player"]',           # Any player class
            '#tiktok-web-player',          # ID selector
            '[data-e2e="live-video"]',     # Another live selector
            '.live-container video',       # Container video
        ]
        
        for selector in selectors:
            try:
                element = await page.wait_for_selector(selector, timeout=config.element_wait_timeout)
                if element:
                    logger.info(f"Viewer {self.viewer_id}: Found element with selector: {selector}")
                    return True
            except PlaywrightTimeout:
                continue
            except Exception as e:
                logger.debug(f"Viewer {self.viewer_id}: Selector {selector} error: {e}")
                continue
                
        return False
    
    async def _keep_alive(self, page):
        """Enhanced keep alive with interactive features."""
        start_time = time.time()
        last_action = time.time()
        interaction_cycle = 0
        
        while True:
            try:
                # Check if session should continue (based on config)
                if time.time() - start_time > config.session_max_duration:
                    logger.info(f"Viewer {self.viewer_id}: Session time limit reached ({config.session_max_duration}s)")
                    break
                    
                # Perform random actions to simulate human behavior
                await asyncio.sleep(random.uniform(config.keepalive_min_interval, config.keepalive_max_interval))
                await page.mouse.move(random.randint(300, 600), random.randint(300, 500))
                last_action = time.time()
                
                # Add interactive features every few cycles
                interaction_cycle += 1
                if interaction_cycle % 3 == 0:  # Every 3rd cycle
                    # Simulate content context (in reality this would come from stream analysis)
                    context = None  # Would be populated with actual stream insights
                    await self.interactive_controller.auto_interact(page, context)
                    
                    # Log interaction stats periodically
                    if interaction_cycle % 9 == 0:  # Every 9th cycle
                        stats = self.interactive_controller.get_interaction_stats()
                        logger.info(f"Viewer {self.viewer_id}: Interaction stats - "
                                  f"Comments: {stats.get('comments_sent', 0)}, "
                                  f"Reactions: {stats.get('reactions_made', 0)}")
                
                # Log heartbeat
                elapsed = int(time.time() - start_time)
                logger.info(f"Viewer {self.viewer_id}: Still watching... ({elapsed}s)")
                
            except Exception as e:
                logger.warning(f"Viewer {self.viewer_id}: Keep alive error: {e}")
                # Continue watching despite minor errors
                await asyncio.sleep(10)


async def main():
    live_url = config.live_url
    num_viewers = config.num_viewers
    
    logger.info(f"Starting {num_viewers} viewers for {live_url}")
    logger.info("Make sure you are LIVE on TikTok right now!")
    logger.info("Starting in 3 seconds...")
    await asyncio.sleep(3)
    
    # Create folder for screenshots
    if config.debug_screenshots and not os.path.exists(config.screenshot_dir):
        os.makedirs(config.screenshot_dir)
    
    # Health check proxies
    await proxy_manager.health_check()
    
    tasks = []
    for i in range(num_viewers):
        proxy = proxy_manager.get_proxy()
        viewer = TikTokViewer(viewer_id=i+1, proxy=proxy)
        tasks.append(viewer.start(live_url))
        
        # Stagger viewer start times
        if i < num_viewers - 1:  # No need to wait after the last viewer
            await asyncio.sleep(2)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    success_count = sum(1 for result in results if result is True)
    logger.info(f"\nCompleted. {success_count}/{num_viewers} viewers succeeded.")
    
    # Show any errors
    errors = [result for result in results if isinstance(result, Exception)]
    if errors:
        logger.error(f"{len(errors)} viewers encountered errors:")
        for i, error in enumerate(errors):
            logger.error(f"  Viewer error {i+1}: {error}")

if __name__ == "__main__":
    asyncio.run(main())