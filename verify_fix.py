from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        all_logs = []
        page.on("console", lambda msg: all_logs.append({"type": msg.type, "text": msg.text}))
        
        page_errors = []
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
        
        print("="*70)
        print("FINAL VERIFICATION - PROXIES PAGE WITH FORM SUBMISSION")
        print("="*70)
        
        # Login
        print("\n[Step 1] Logging in...")
        page.goto('http://localhost:8000/accounts/login/')
        page.wait_for_load_state('networkidle')
        page.fill('input[name="username"]', 'admin')
        page.fill('input[name="password"]', 'password')
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(2000)
        print("  [OK] Logged in")
        
        # Load proxies page
        print("\n[Step 2] Loading proxies page...")
        page.goto('http://localhost:8000/proxies/')
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(2000)
        page.screenshot(path='verify_01_loaded.png', full_page=True)
        print("  [OK] Page loaded")
        
        # Open modal
        print("\n[Step 3] Opening Add Proxy modal...")
        page.click('button[data-bs-target="#addProxyModal"]')
        page.wait_for_timeout(2000)
        page.wait_for_selector('#addProxyModal.show', timeout=5000)
        page.screenshot(path='verify_02_modal.png', full_page=True)
        print("  [OK] Modal opened")
        
        # Fill form
        print("\n[Step 4] Filling form...")
        page.fill('#proxy_url', 'http://test-proxy.example.com:8080')
        print("  [OK] Form filled")
        
        # Submit via fetch and capture response
        print("\n[Step 5] Submitting form via fetch...")
        
        # Clear previous logs
        all_logs.clear()
        page_errors.clear()
        
        # Execute fetch and get response
        response = page.evaluate("""
            async () => {
                const form = document.querySelector('#manual form[data-action="add"]');
                const formData = new FormData(form);
                
                try {
                    const resp = await fetch('/proxies/', {
                        method: 'POST',
                        body: formData,
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    });
                    
                    const contentType = resp.headers.get('content-type');
                    const text = await resp.text();
                    
                    return {
                        status: resp.status,
                        contentType: contentType,
                        isJson: contentType && contentType.includes('application/json'),
                        text: text.substring(0, 500) // First 500 chars
                    };
                } catch (error) {
                    return { error: error.message };
                }
            }
        """)
        
        print(f"  Response status: {response.get('status')}")
        print(f"  Content-Type: {response.get('contentType')}")
        print(f"  Is JSON: {response.get('isJson')}")
        
        if response.get('error'):
            print(f"  [ERROR] Fetch error: {response['error']}")
        elif not response.get('isJson'):
            print("  [ERROR] Server returned HTML instead of JSON!")
            print(f"  Response preview: {response.get('text', '')[:200]}")
        else:
            print("  [OK] Server returned JSON response")
        
        page.wait_for_timeout(2000)
        page.screenshot(path='verify_03_after_submit.png', full_page=True)
        
        # Check for errors
        print("\n[Step 6] Checking for errors...")
        
        if page_errors:
            print(f"  [ERROR] JS errors: {len(page_errors)}")
            for err in page_errors:
                print(f"    - {err}")
        else:
            print("  [OK] No JavaScript errors")
        
        error_logs = [log for log in all_logs if log['type'] == 'error']
        if error_logs:
            print(f"  [ERROR] Console errors: {len(error_logs)}")
            for log in error_logs:
                print(f"    - {log['text']}")
        else:
            print("  [OK] No console errors")
        
        # Check page content
        body_text = page.inner_text('body').strip()
        print(f"\n  Page content length: {len(body_text)} chars")
        
        if len(body_text) < 100:
            print("  [FAIL] Page is BLANK!")
            is_blank = True
        else:
            print("  [OK] Page has content")
            is_blank = False
        
        # Final summary
        print("\n" + "="*70)
        print("VERIFICATION SUMMARY")
        print("="*70)
        print(f"AJAX JSON response: {'OK' if response.get('isJson') else 'FAILED'}")
        print(f"Page blanking: {'YES - ISSUE!' if is_blank else 'No'}")
        print(f"JavaScript errors: {len(page_errors)}")
        print(f"Console errors: {len(error_logs)}")
        
        if response.get('isJson') and not is_blank and not page_errors:
            print("\n[PASS] All verifications passed! Page is working correctly.")
        else:
            print("\n[FAIL] Issues were found!")
        
        browser.close()

if __name__ == "__main__":
    main()
