import asyncio
import random
import os
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from fake_useragent import UserAgent

class TikTokViewer:
    def __init__(self, proxy=None):
        self.proxy = proxy
        self.ua = UserAgent(fallback='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
    async def start(self, live_url, viewer_id):
        browser = None
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
                    print(f"Viewer {viewer_id}: Using proxy")
                
                print(f"Viewer {viewer_id}: Starting browser...")
                browser = await p.chromium.launch(**launch_options)
                
                context = await browser.new_context(
                    viewport={'width': 1366, 'height': 768},
                    user_agent=self.ua.random,
                    locale='en-US',
                    timezone_id='America/New_York',
                    color_scheme='light'
                )
                
                # Mask automation
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                    window.chrome = { runtime: {} };
                    Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
                """)
                
                page = await context.new_page()
                
                # Block images to load faster, but allow video
                await page.route("**/*", lambda route: route.continue_() if "video" in route.request.url else route.continue_())
                
                print(f"Viewer {viewer_id}: Loading page...")
                
                # Go to page and wait longer
                response = await page.goto(live_url, wait_until='load', timeout=60000)
                print(f"Viewer {viewer_id}: Page loaded (status: {response.status})")
                
                # Wait for TikTok to render
                await asyncio.sleep(5)
                
                # Try to find video with multiple selectors
                video_found = False
                selectors = [
                    'video',  # Standard video
                    'canvas',  # TikTok sometimes uses canvas
                    '[data-e2e="live-content"]',  # Live container
                    '.tiktok-web-player',  # Player container
                    '[class*="player"]',  # Any player class
                    '#tiktok-web-player',  # ID selector
                ]
                
                for selector in selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=10000)
                        print(f"Viewer {viewer_id}: Found element: {selector}")
                        video_found = True
                        break
                    except:
                        continue
                
                if not video_found:
                    # Take screenshot to see what's there
                    screenshot_path = f"debug_viewer_{viewer_id}.png"
                    await page.screenshot(path=screenshot_path, full_page=True)
                    print(f"Viewer {viewer_id}: ❌ No video found")
                    print(f"Viewer {viewer_id}: Screenshot saved: {screenshot_path}")
                    
                    # Check if there's a login button or age restriction
                    html = await page.content()
                    if "login" in html.lower():
                        print(f"Viewer {viewer_id}: TikTok wants login")
                    elif "age" in html.lower():
                        print(f"Viewer {viewer_id}: Age restriction")
                    elif "not available" in html.lower():
                        print(f"Viewer {viewer_id}: Stream not available")
                    else:
                        print(f"Viewer {viewer_id}: Unknown issue (check screenshot)")
                    return
                
                print(f"Viewer {viewer_id}: ✅ WATCHING")
                
                # Keep alive
                while True:
                    await asyncio.sleep(random.uniform(30, 60))
                    await page.mouse.move(random.randint(300, 600), random.randint(300, 500))
                    
        except Exception as e:
            print(f"Viewer {viewer_id}: ❌ Error: {str(e)[:60]}")
        finally:
            if browser:
                await browser.close()

async def main():
    live_url = "https://www.tiktok.com/@khamish92/live"
    num_viewers = 3  # Start with just 3 for testing
    
    print(f"Starting {num_viewers} viewers for {live_url}")
    print("⚠️  Make sure you are LIVE on TikTok right now!")
    print("Starting in 3 seconds...")
    await asyncio.sleep(3)
    
    # Create folder for screenshots
    if not os.path.exists('screenshots'):
        os.makedirs('screenshots')
    
    proxies = []
    try:
        with open('proxies.txt', 'r') as f:
            proxies = [line.strip() for line in f if line.strip()]
        print(f"Loaded {len(proxies)} proxies\n")
    except:
        print("No proxies, using direct connection\n")
    
    tasks = []
    for i in range(num_viewers):
        proxy = proxies[i % len(proxies)] if proxies else None
        viewer = TikTokViewer(proxy=proxy)
        tasks.append(viewer.start(live_url, i+1))
        await asyncio.sleep(2)
    
    await asyncio.gather(*tasks, return_exceptions=True)
    print("\nDone. Check screenshots folder if viewers failed.")

if __name__ == "__main__":
    asyncio.run(main())