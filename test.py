import asyncio
from playwright.async_api import async_playwright

async def test_no_proxy():
    print("TEST 1: Loading TikTok WITHOUT proxy...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        page = await browser.new_page()
        try:
            response = await page.goto("https://www.tiktok.com/@khamish92/live", timeout=30000)
            print(f"✅ TikTok loaded! Status: {response.status}")
            await page.screenshot(path="test_no_proxy.png")
            print("Screenshot saved: test_no_proxy.png")
        except Exception as e:
            print(f"❌ Failed: {str(e)[:80]}")
        await browser.close()

async def test_with_proxy():
    print("\nTEST 2: Loading Google WITH proxy (testing proxy works)...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox'],
            proxy={'server': 'http://khamis1992:zWoUVToxxgp3nYGE@proxy.packetstream.io:31112'}
        )
        page = await browser.new_page()
        try:
            response = await page.goto("https://www.google.com", timeout=30000)
            print(f"✅ Google loaded via proxy! Status: {response.status}")
        except Exception as e:
            print(f"❌ Proxy can't even load Google: {str(e)[:80]}")
            print("Your proxy is NOT working!")
            await browser.close()
            return
        await browser.close()
    
    print("\nTEST 3: Loading TikTok WITH proxy...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox'],
            proxy={'server': 'http://khamis1992:zWoUVToxxgp3nYGE@proxy.packetstream.io:31112'}
        )
        page = await browser.new_page()
        try:
            response = await page.goto("https://www.tiktok.com/@khamish92/live", timeout=60000)
            print(f"✅ TikTok loaded via proxy! Status: {response.status}")
            await page.screenshot(path="test_with_proxy.png")
            print("Screenshot saved: test_with_proxy.png")
        except Exception as e:
            print(f"❌ Proxy can't load TikTok: {str(e)[:80]}")
            print("TikTok is BLOCKING your PacketStream proxy!")
        await browser.close()

async def main():
    print("=== DIAGNOSTIC TEST ===\n")
    await test_no_proxy()
    await test_with_proxy()
    print("\n=== DONE ===")
    print("Check test_no_proxy.png and test_with_proxy.png in your folder")

asyncio.run(main())