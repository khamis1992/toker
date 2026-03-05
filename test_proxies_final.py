from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        # Capture console logs
        console_logs = []
        page.on("console", lambda msg: console_logs.append({
            "type": msg.type,
            "text": msg.text
        }))
        
        # Capture page errors
        page_errors = []
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
        
        # Track network requests/responses
        failed_requests = []
        page.on("response", lambda resp: 
            failed_requests.append(f"{resp.status} {resp.url}") if resp.status >= 400 else None
        )
        
        print("="*70)
        print("TESTING TIKTOK BOT DASHBOARD - PROXIES PAGE")
        print("Credentials: admin / password")
        print("="*70)
        
        # Step 1: Navigate to login page
        print("\n[Step 1] Navigating to login page...")
        response = page.goto('http://localhost:8000/accounts/login/')
        page.wait_for_load_state('networkidle')
        print(f"  Login page status: {response.status}")
        page.screenshot(path='test_01_login_page.png', full_page=True)
        print("  [OK] Login page loaded")
        
        # Step 2: Login with CORRECT credentials
        print("\n[Step 2] Logging in with admin/password...")
        
        # Wait for form to be ready
        page.wait_for_selector('input[name="username"]')
        
        # Fill in credentials
        page.fill('input[name="username"]', 'admin')
        page.fill('input[name="password"]', 'password')  # CORRECT PASSWORD
        
        # Submit form and wait for navigation
        print("  Submitting login form...")
        page.click('button[type="submit"]')
        
        # Wait for navigation to complete
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(3000)
        
        # Check if we're still on login page (login failed) or redirected
        current_url = page.url
        print(f"  Current URL after login: {current_url}")
        page.screenshot(path='test_02_after_login.png', full_page=True)
        
        if '/accounts/login/' in current_url:
            print("  [ERROR] Still on login page - login failed!")
            error_div = page.locator('.alert-danger')
            if error_div.is_visible():
                error_text = error_div.inner_text()
                print(f"  Error message: {error_text}")
            return  # Exit early
        else:
            print("  [OK] Login successful - redirected to dashboard")
        
        # Step 3: Navigate to proxies page
        print("\n[Step 3] Navigating to /proxies/ page...")
        response = page.goto('http://localhost:8000/proxies/')
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(2000)
        
        current_url = page.url
        print(f"  Current URL: {current_url}")
        print(f"  Response status: {response.status}")
        page.screenshot(path='test_03_proxies_page.png', full_page=True)
        
        # Check if page is blank
        body_text = page.inner_text('body').strip()
        print(f"  Page body text length: {len(body_text)} characters")
        
        if len(body_text) < 100:
            print("  [WARNING] Page appears to be BLANK or nearly blank!")
            print(f"  Body content preview: {body_text[:300]}")
        else:
            print("  [OK] Proxies page loaded with content")
        
        # Step 4: Find and click "Add Proxy" button
        print("\n[Step 4] Looking for 'Add Proxy' button...")
        
        selectors = [
            'button[data-bs-target="#addProxyModal"]',
            'button:has-text("Add Proxy")',
            'button:has-text("Add Your First Proxy")',
            'text=Add Proxy',
            '.btn-primary',
        ]
        
        button_found = False
        
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.is_visible():
                    button_text = locator.inner_text()
                    print(f"  [OK] Found button: '{button_text}'")
                    print(f"    Using selector: {selector}")
                    
                    # Click the button
                    print("\n[Step 5] Clicking the button...")
                    locator.click()
                    page.wait_for_timeout(2000)
                    page.screenshot(path='test_04_after_click.png', full_page=True)
                    
                    button_found = True
                    break
            except Exception as e:
                continue
        
        if not button_found:
            print("  [ERROR] Could not find 'Add Proxy' button")
            buttons = page.locator('button').all()
            print(f"\n  Available buttons ({len(buttons)}):")
            for i, btn in enumerate(buttons[:15]):
                try:
                    text = btn.inner_text()
                    visible = btn.is_visible()
                    print(f"    {i+1}. '{text}' (visible: {visible})")
                except:
                    print(f"    {i+1}. [could not read button]")
        else:
            # Step 6: Check if modal appeared or page blanked
            print("\n[Step 6] Checking page state after click...")
            page.wait_for_timeout(1000)
            page.screenshot(path='test_05_final_state.png', full_page=True)
            
            modal_selectors = [
                '#addProxyModal',
                '.modal.show',
                '.modal.fade.show',
                '.modal-dialog',
            ]
            
            modal_found = False
            for modal_sel in modal_selectors:
                try:
                    modal = page.locator(modal_sel).first
                    if modal.is_visible():
                        print(f"  [OK] Modal found with selector: {modal_sel}")
                        modal_found = True
                        break
                except:
                    continue
            
            if not modal_found:
                print("  [WARNING] No modal detected")
            
            body_after = page.inner_text('body').strip()
            if len(body_after) < 100:
                print("  [WARNING] Page appears BLANK after clicking!")
                print(f"  Body content: {body_after[:300]}")
            else:
                print(f"  [OK] Page has content ({len(body_after)} chars)")
        
        # Print any errors
        print("\n" + "="*70)
        print("ERROR REPORT")
        print("="*70)
        
        if page_errors:
            print(f"\n[ERROR] JavaScript Errors ({len(page_errors)}):")
            for i, error in enumerate(page_errors, 1):
                print(f"  {i}. {error}")
        else:
            print("\n[OK] No JavaScript errors detected")
        
        error_logs = [log for log in console_logs if log['type'] == 'error']
        if error_logs:
            print(f"\n[ERROR] Console Error Logs ({len(error_logs)}):")
            for i, log in enumerate(error_logs, 1):
                print(f"  {i}. {log['text']}")
        else:
            print("[OK] No console error logs")
        
        if failed_requests:
            print(f"\n[ERROR] Failed HTTP Requests ({len(failed_requests)}):")
            for i, req in enumerate(failed_requests[:10], 1):
                print(f"  {i}. {req}")
        else:
            print("[OK] No failed HTTP requests")
        
        # Summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print("Screenshots saved:")
        print("  - test_01_login_page.png")
        print("  - test_02_after_login.png")
        print("  - test_03_proxies_page.png")
        print("  - test_04_after_click.png")
        print("  - test_05_final_state.png")
        
        has_issues = bool(page_errors or error_logs or len(body_text) < 100 or not button_found)
        
        if has_issues:
            print("\n[WARNING] ISSUES DETECTED:")
            if len(body_text) < 100:
                print("  - Page is blank or nearly blank")
            if not button_found:
                print("  - Add Proxy button not found")
            if page_errors:
                print(f"  - {len(page_errors)} JavaScript errors")
            if error_logs:
                print(f"  - {len(error_logs)} console errors")
        else:
            print("\n[OK] All checks passed - Page is working correctly with password 'password'")
        
        browser.close()

if __name__ == "__main__":
    main()
