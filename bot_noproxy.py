import asyncio
import random
from playwright.async_api import async_playwright
from fake_useragent import UserAgent

class TikTokViewer:
    def __init__(self):
        self.ua = UserAgent(fallback='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
    async def start(self, live_url, viewer_id):
        browser = None
        try:
            async with async_playwright() as p:
                args = [
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--window-size=1366,768'
                ]
                
                print(f"Viewer {viewer_id}: Starting browser...")
                browser = await p.chromium.launch(headless=True, args=args)
                
                context = await browser.new_context(
                    viewport={'width': 1366, 'height': 768},
                    user_agent=self.ua.random,
                    locale='en-US',
                    timezone_id='America/New_York'
                )
                
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    window.chrome = { runtime: {} };
                """)
                
                page = await context.new_page()
                
                print(f"Viewer {viewer_id}: Loading TikTok...")
                await page.goto(live_url, wait_until='load', timeout=60000)
                
                # Wait for page to fully render
                await asyncio.sleep(5)
                
                # Try multiple selectors
                selectors = ['video', 'canvas', '[class*="player"]', '[data-e2e="live-content"]']
                video_found = False
                
                for selector in selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=10000)
                        print(f"Viewer {viewer_id}: ✅ WATCHING LIVE (found: {selector})")
                        video_found = True
                        break
                    except:
                        continue
                
                if not video_found:
                    await page.screenshot(path=f"debug_{viewer_id}.png")
                    print(f"Viewer {viewer_id}: ❌ No video. Screenshot saved: debug_{viewer_id}.png")
                    
                    # Print page title to see what loaded
                    title = await page.title()
                    print(f"Viewer {viewer_id}: Page title: {title}")
                    return
                
                # Keep watching
                minutes = 0
                while True:
                    await asyncio.sleep(random.uniform(25, 45))
                    await page.mouse.move(random.randint(200, 800), random.randint(200, 500))
                    minutes += 1
                    if minutes % 2 == 0:
                        print(f"Viewer {viewer_id}: Still watching... ({minutes} min)")
                    
        except Exception as e:
            print(f"Viewer {viewer_id}: ❌ Error: {str(e)[:80]}")
        finally:
            if browser:
                await browser.close()

async def main():
    live_url = "https://www.tiktok.com/@khamish92/live"
    num_viewers = 5  # 5 viewers without proxy
    
    print(f"Starting {num_viewers} viewers (NO PROXY)")
    print(f"Target: {live_url}")
    print("⚠️  ARE YOU LIVE ON TIKTOK RIGHT NOW? ⚠️")
    print("")
    
    input("Press ENTER when you are live...")
    
    tasks = []
    for i in range(num_viewers):
        viewer = TikTokViewer()
        tasks.append(viewer.start(live_url, i+1))
        await asyncio.sleep(3)
    
    await asyncio.gather(*tasks, return_exceptions=True)
    print("\nAll viewers stopped.")

if __name__ == "__main__":
    asyncio.run(main())