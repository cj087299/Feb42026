from playwright.sync_api import sync_playwright
import time

def verify_reports():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Capture console logs
        page.on("console", lambda msg: print(f"Browser Console: {msg.text}"))
        page.on("pageerror", lambda exc: print(f"Browser Error: {exc}"))

        # Login
        print("Navigating to login...")
        page.goto("http://localhost:8080/login")
        page.fill('input[name="email"]', "admin@vzt.com")
        page.fill('input[name="password"]', "admin1234")
        page.click("button[type=submit]")

        # Wait for login
        print("Waiting for dashboard...")
        page.wait_for_url("http://localhost:8080/")

        # Navigate to Reports directly since dashboard might be JSON
        print("Navigating to reports page directly...")
        page.goto("http://localhost:8080/reports")

        # Take screenshot of initial state
        page.screenshot(path="verification/reports_initial.png")
        print("Initial screenshot taken: verification/reports_initial.png")

        # Toggle Comparison
        print("Toggling comparison...")
        try:
            page.check("#compareToggle", timeout=5000)
            time.sleep(0.5)
            page.screenshot(path="verification/reports_comparison.png")
            print("Comparison toggle screenshot taken: verification/reports_comparison.png")
        except Exception as e:
            print(f"Comparison toggle failed: {e}")
            page.screenshot(path="verification/error_comparison.png")

        # Attempt to run report (will fail but show error or empty state)
        print("Running report...")
        try:
            page.click("#runReportBtn", timeout=5000)

            # Wait for loading or error
            time.sleep(2)
            page.screenshot(path="verification/reports_run.png")
            print("Run report screenshot taken: verification/reports_run.png")
        except Exception as e:
             print(f"Run report failed: {e}")

        browser.close()

if __name__ == "__main__":
    verify_reports()
