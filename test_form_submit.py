from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        # Capture ALL console messages
        console_logs = []
        page.on("console", lambda msg: console_logs.append({
            "type": msg.type,
            "text": msg.text
        }))
        
        # Capture page errors
        page_errors = []
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
        
        # Track network failures
        failed_requests = []
        def handle_response(response):
            if response.status >= 400:
                failed_requests.append(f"{response.status} {response.url}")
        page.on("response", handle_response)
        
        print("="*70)
        print("COMPREHENSIVE PROXIES PAGE TEST - INCLUDING FORM SUBMISSION")
        print("="*70)
        
        # Step 1: Login
        print("\n[Step 1] Logging in...")
        page.goto('http://localhost:8000/accounts/login/')
        page.wait_for_load_state('networkidle')
        page.fill('input[name="username"]', 'admin')
        page.fill('input[name="password"]', 'password')
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(2000)
        
        if '/accounts/login/' in page.url:
            print("  [FAIL] Login failed!")
            return
        print("  [OK] Logged in")
        
        # Step 2: Go to proxies page
        print("\n[Step 2] Loading proxies page...")
        page.goto('http://localhost:8000/proxies/')
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(2000)
        page.screenshot(path='test_proxies_loaded.png', full_page=True)
        
        body_text = page.inner_text('body').strip()
        print(f"  Page content length: {len(body_text)} chars")
        
        # Step 3: Click Add Proxy button
        print("\n[Step 3] Clicking 'Add Proxy' button...")
        add_btn = page.locator('button[data-bs-target="#addProxyModal"]').first
        if not add_btn.is_visible():
            print("  [FAIL] Add Proxy button not visible!")
            return
        
        add_btn.click()
        page.wait_for_timeout(1500)
        page.screenshot(path='test_modal_open.png', full_page=True)
        print("  [OK] Modal opened")
        
        # Step 4: Fill in the proxy form
        print("\n[Step 4] Filling proxy form...")
        proxy_input = page.locator('#proxy_url').first
        if not proxy_input.is_visible():
            print("  [FAIL] Proxy URL input not visible!")
            return
        
        proxy_input.fill('http://test-proxy.example.com:8080')
        print("  [OK] Filled proxy URL")
        
        # Step 5: Submit the form - THIS IS WHERE BLANKING MIGHT OCCUR
        print("\n[Step 5] Submitting form (testing for blanking)...")
        submit_btn = page.locator('#manual button[type="submit"]').first
        
        # Clear previous logs
        console_logs.clear()
        page_errors.clear()
        failed_requests.clear()
        
        # Click submit
        submit_btn.click()
        
        # Wait for response
        page.wait_for_timeout(3000)
        page.screenshot(path='test_after_submit.png', full_page=True)
        
        # Check page state
        body_after = page.inner_text('body').strip()
        current_url = page.url
        print(f"  Current URL: {current_url}")
        print(f"  Page content length: {len(body_after)} chars")
        
        if len(body_after) < 100:
            print("  [FAIL] Page appears BLANK after form submission!")
            is_blank = True
        else:
            print("  [OK] Page has content after submission")
            is_blank = False
        
        # Step 6: Check for errors
        print("\n[Step 6] Checking for errors...")
        
        if page_errors:
            print(f"  [ERROR] JavaScript errors ({len(page_errors)}):")
            for err in page_errors:
                print(f"    - {err}")
        else:
            print("  [OK] No JavaScript errors")
        
        error_logs = [log for log in console_logs if log['type'] == 'error']
        if error_logs:
            print(f"  [ERROR] Console errors ({len(error_logs)}):")
            for log in error_logs:
                print(f"    - {log['text']}")
        else:
            print("  [OK] No console error logs")
        
        if failed_requests:
            print(f"  [ERROR] Failed requests ({len(failed_requests)}):")
            for req in failed_requests:
                print(f"    - {req}")
        else:
            print("  [OK] No failed HTTP requests")
        
        # Final summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Page blank after submit: {'YES - ISSUE FOUND!' if is_blank else 'No'}")
        print(f"JavaScript errors: {len(page_errors)}")
        print(f"Console errors: {len(error_logs)}")
        print(f"Failed requests: {len(failed_requests)}")
        
        if is_blank or page_errors or error_logs:
            print("\n[FAIL] Issues detected!")
        else:
            print("\n[PASS] All tests passed - no blanking detected")
        
        browser.close()

if __name__ == "__main__":
    main()
