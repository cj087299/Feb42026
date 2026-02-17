
import time
from playwright.sync_api import sync_playwright

def verify_fixes():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 720})
        page = context.new_page()

        # Login
        print("Logging in...")
        page.goto("http://localhost:8080/login")
        page.fill("input[name='email']", "admin@vzt.com")
        page.fill("input[name='password']", "admin1234")
        page.click("button[type='submit']")
        page.wait_for_url("http://localhost:8080/")

        # Verify Invoices Page
        print("Navigating to Invoices...")
        page.goto("http://localhost:8080/invoices")
        page.wait_for_selector("h1")
        time.sleep(2) # Wait for data load

        # Check for Export All button
        export_all_btn = page.query_selector("button[title='Export full dataset']")
        if export_all_btn:
            print("Export All button found on Invoices page.")
        else:
            print("ERROR: Export All button NOT found on Invoices page.")

        page.screenshot(path="verification/invoices_fixed.png")
        print("Screenshot saved: verification/invoices_fixed.png")

        # Verify Customer Settings Page
        print("Navigating to Customer Settings...")
        page.goto("http://localhost:8080/customer-settings")
        page.wait_for_selector("h2")
        time.sleep(2)

        # Check for branded buttons
        buttons = page.query_selector_all(".btn-action")
        if len(buttons) >= 3:
            print(f"Found {len(buttons)} branded export buttons on Customer Settings page.")
        else:
            print(f"ERROR: Expected at least 3 branded buttons, found {len(buttons)}.")

        page.screenshot(path="verification/customer_settings_fixed.png")
        print("Screenshot saved: verification/customer_settings_fixed.png")

        browser.close()

if __name__ == "__main__":
    verify_fixes()
