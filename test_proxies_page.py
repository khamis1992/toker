from playwright.sync_api import sync_playwright
import json

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Capture console logs
        console_logs = []
        page.on("console", lambda msg: console_logs.append({
            "type": msg.type,
            "text": msg.text
        }))
        
        # Capture page errors
        page_errors = []
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
        
        # Navigate to the proxies page
        print("Navigating to http://localhost:8000/proxies/...")
        page.goto('http://localhost:8000/proxies/')
        page.wait_for_load_state('networkidle')
        
        # Take initial screenshot
        print("Taking initial screenshot...")
        page.screenshot(path='proxies_initial.png', full_page=True)
        
        # Get page content
        content = page.content()
        print(f"\nPage loaded. Content length: {len(content)}")
        
        # Check if page is blank
        body_text = page.inner_text('body')
        print(f"Body text length: {len(body_text.strip())}")
        
        if len(body_text.strip()) == 0:
            print("⚠️ WARNING: Page appears to be BLANK!")
        
        # Try to find and click "add proxy" button
        print("\nLooking for 'add proxy' button...")
        
        # Try different selectors
        selectors = [
            'text=Add Proxy',
            'text=add proxy',
            'text=Add proxy',
            'button:has-text("Proxy")',
            '[data-testid*="proxy"]',
            'button',
            'a:has-text("Proxy")',
            'role=button',
        ]
        
        button_found = False
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.is_visible():
                    print(f"✓ Found button with selector: {selector}")
                    print(f"  Button text: {locator.inner_text()}")
                    
                    # Click the button
                    print("\nClicking the button...")
                    locator.click()
                    page.wait_for_timeout(2000)  # Wait for any transitions
                    
                    # Take screenshot after click
                    print("Taking screenshot after click...")
                    page.screenshot(path='proxies_after_click.png', full_page=True)
                    
                    # Check if page is blank after click
                    new_body_text = page.inner_text('body')
                    print(f"Body text after click length: {len(new_body_text.strip())}")
                    
                    if len(new_body_text.strip()) == 0:
                        print("⚠️ WARNING: Page appears BLANK after clicking!")
                    
                    button_found = True
                    break
            except Exception as e:
                continue
        
        if not button_found:
            print("✗ Could not find 'add proxy' button with any selector")
            # List all buttons on page
            buttons = page.locator('button').all()
            print(f"\nFound {len(buttons)} button(s) on page:")
            for i, btn in enumerate(buttons):
                try:
                    text = btn.inner_text()
                    visible = btn.is_visible()
                    print(f"  Button {i}: '{text}' (visible: {visible})")
                except:
                    print(f"  Button {i}: [could not get text]")
        
        # Print console logs
        if console_logs:
            print("\n" + "="*60)
            print("CONSOLE LOGS:")
            print("="*60)
            for log in console_logs:
                print(f"[{log['type']}] {log['text']}")
        
        # Print page errors
        if page_errors:
            print("\n" + "="*60)
            print("PAGE ERRORS:")
            print("="*60)
            for error in page_errors:
                print(f"ERROR: {error}")
        
        # Get network errors
        network_errors = []
        page.on("response", lambda resp: 
            network_errors.append(f"{resp.status} {resp.url}") if resp.status >= 400 else None
        )
        
        browser.close()
        
        # Summary
        print("\n" + "="*60)
        print("SUMMARY:")
        print("="*60)
        print(f"Initial screenshot: proxies_initial.png")
        print(f"After click screenshot: proxies_after_click.png")
        print(f"Console logs: {len(console_logs)}")
        print(f"Page errors: {len(page_errors)}")
        
        if page_errors or any(log['type'] == 'error' for log in console_logs):
            print("\n⚠️ ISSUES DETECTED - Please check the screenshots and logs above")
        else:
            print("\n✓ No JavaScript errors detected")

if __name__ == "__main__":
    main()
