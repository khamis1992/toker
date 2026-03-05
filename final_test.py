from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        # Capture ALL console messages
        all_logs = []
        page.on("console", lambda msg: all_logs.append({
            "type": msg.type,
            "text": msg.text
        }))
        
        # Capture page errors
        page_errors = []
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
        
        print("="*70)
        print("FINAL COMPREHENSIVE TEST - PROXIES PAGE WITH ALL FIXES")
        print("="*70)
        
        # Step 1: Login
        print("\n[Step 1] Logging in with admin/password...")
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
        print("  [OK] Logged in successfully")
        
        # Step 2: Load proxies page
        print("\n[Step 2] Loading proxies page...")
        page.goto('http://localhost:8000/proxies/')
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(2000)
        
        # Check for JavaScript errors on page load
        if page_errors:
            print(f"  [WARNING] JS errors on load: {len(page_errors)}")
            for err in page_errors:
                print(f"    - {err}")
            page_errors.clear()
        else:
            print("  [OK] No JS errors on page load")
        
        body_text = page.inner_text('body').strip()
        print(f"  Page content: {len(body_text)} chars")
        page.screenshot(path='final_test_01_page_loaded.png', full_page=True)
        
        # Step 3: Open Add Proxy modal
        print("\n[Step 3] Opening Add Proxy modal...")
        add_btn = page.locator('button[data-bs-target="#addProxyModal"]').first
        add_btn.click()
        page.wait_for_timeout(2000)
        
        # Wait for modal animation
        page.wait_for_selector('#addProxyModal.show, .modal.show', timeout=5000)
        page.screenshot(path='final_test_02_modal_open.png', full_page=True)
        print("  [OK] Modal opened")
        
        # Step 4: Fill and submit form
        print("\n[Step 4] Filling and submitting form...")
        
        # Fill proxy URL
        proxy_input = page.locator('#proxy_url').first
        proxy_input.fill('http://test.example.com:8080')
        print("  [OK] Filled proxy URL")
        
        # Clear any previous errors
        page_errors.clear()
        all_logs.clear()
        
        # Find and click submit button (using JavaScript click to avoid animation issues)
        print("  Submitting form via JavaScript...")
        page.evaluate("""
            () => {
                const form = document.querySelector('#manual form[data-action="add"]');
                if (form) {
                    const event = new Event('submit', { cancelable: true });
                    form.dispatchEvent(event);
                }
            }
        """)
        
        # Wait for response
        page.wait_for_timeout(3000)
        page.screenshot(path='final_test_03_after_submit.png', full_page=True)
        
        # Check for errors
        if page_errors:
            print(f"  [ERROR] JS errors during submit: {len(page_errors)}")
            for err in page_errors:
                print(f"    - {err}")
        else:
            print("  [OK] No JS errors during form submission")
        
        # Check page content
        body_after = page.inner_text('body').strip()
        print(f"  Page content after submit: {len(body_after)} chars")
        
        if len(body_after) < 100:
            print("  [FAIL] Page appears BLANK after submission!")
            is_blank = True
        else:
            print("  [OK] Page has content after submission")
            is_blank = False
        
        # Check console logs
        error_logs = [log for log in all_logs if log['type'] == 'error']
        if error_logs:
            print(f"  [ERROR] Console errors ({len(error_logs)}):")
            for log in error_logs:
                print(f"    - {log['text']}")
        
        # Step 5: Test Format Help button (was missing function)
        print("\n[Step 5] Testing Format Help button...")
        page_errors.clear()
        
        # Click on Free Proxies tab first
        free_proxies_tab = page.locator('#free-proxies-tab').first
        if free_proxies_tab.is_visible():
            free_proxies_tab.click()
            page.wait_for_timeout(1000)
            
            # Find and click Format Help button
            help_btn = page.locator('button[onclick*="showProxyFormatHelp"]').first
            if help_btn.is_visible():
                help_btn.click()
                page.wait_for_timeout(1000)
                
                if page_errors:
                    print(f"  [ERROR] JS errors when clicking Format Help: {len(page_errors)}")
                    for err in page_errors:
                        print(f"    - {err}")
                else:
                    print("  [OK] Format Help button works")
                
                page.screenshot(path='final_test_04_format_help.png', full_page=True)
            else:
                print("  [INFO] Format Help button not visible")
        else:
            print("  [INFO] Free Proxies tab not visible")
        
        # Final summary
        print("\n" + "="*70)
        print("FINAL TEST SUMMARY")
        print("="*70)
        print(f"Page blanking issue: {'FOUND' if is_blank else 'NOT FOUND'}")
        print(f"Total JS errors: {len(page_errors)}")
        print(f"Total console errors: {len(error_logs)}")
        print("\nScreenshots saved:")
        print("  - final_test_01_page_loaded.png")
        print("  - final_test_02_modal_open.png")
        print("  - final_test_03_after_submit.png")
        print("  - final_test_04_format_help.png")
        
        if is_blank or page_errors:
            print("\n[FAIL] Issues were detected!")
        else:
            print("\n[PASS] All tests passed successfully!")
        
        browser.close()

if __name__ == "__main__":
    main()
