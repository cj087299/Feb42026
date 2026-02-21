from playwright.sync_api import sync_playwright
import time

def verify_navigation():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Login
        print("Logging in...")
        page.goto("http://localhost:8080/login")
        page.fill('input[name="email"]', "admin@vzt.com")
        page.fill('input[name="password"]', "admin1234")
        page.click("button[type=submit]")
        page.wait_for_url("http://localhost:8080/")

        # Check for Reports card on Dashboard
        print("Checking Dashboard for Reports card...")
        page.screenshot(path="verification/dashboard_nav.png")
        reports_card = page.query_selector("a[href='/reports']")
        if reports_card:
            print("SUCCESS: Reports card found on dashboard.")
        else:
            print("ERROR: Reports card NOT found on dashboard.")

        # Test Deep Linking
        print("Testing Deep Linking (auto-run ProfitAndLoss)...")
        page.goto("http://localhost:8080/reports?type=ProfitAndLoss")

        # Check if dropdown is set
        selected_value = page.eval_on_selector("#reportType", "el => el.value")
        print(f"Selected Report Type: {selected_value}")
        if selected_value == "ProfitAndLoss":
             print("SUCCESS: Dropdown auto-selected ProfitAndLoss.")
        else:
             print(f"ERROR: Dropdown is {selected_value}, expected ProfitAndLoss.")

        # Check if it tried to run (loading indicator or error)
        # Since we have no creds, it should show error eventually
        time.sleep(2)
        page.screenshot(path="verification/reports_deep_link.png")

        browser.close()

if __name__ == "__main__":
    verify_navigation()
