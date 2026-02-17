from playwright.sync_api import sync_playwright, expect

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # Login
    page.goto("http://localhost:8080/login")
    page.fill("input[name='email']", "cjones@vztsolutions.com")
    page.fill("input[name='password']", "admin1234")
    page.click("button[type='submit']")

    # Wait for login to complete and redirect
    page.wait_for_url("http://localhost:8080/")

    # 1. Verify Invoices Page
    page.goto("http://localhost:8080/invoices")
    page.wait_for_selector("text=Invoices")

    # Check for Export buttons
    expect(page.locator("button:text('CSV')")).to_be_visible()
    expect(page.locator("button:text('Excel')")).to_be_visible()
    expect(page.locator("button:text('PDF')")).to_be_visible()

    page.screenshot(path="verification/invoices_export.png")
    print("Invoices page verified.")

    # 2. Verify Cash Flow Page
    page.goto("http://localhost:8080/cashflow")
    page.wait_for_selector("text=Cash Flow Calendar")

    # Check for Export buttons
    expect(page.locator("button:text('CSV')")).to_be_visible()
    expect(page.locator("button:text('Excel')")).to_be_visible()
    expect(page.locator("button:text('PDF')")).to_be_visible()

    page.screenshot(path="verification/cashflow_export.png")
    print("Cash Flow page verified.")

    # 3. Verify Liquidity Page
    page.goto("http://localhost:8080/liquidity")
    page.wait_for_selector("text=Liquidity Dashboard")

    # Check for Export buttons
    expect(page.locator("button:text('CSV')")).to_be_visible()
    expect(page.locator("button:text('Excel')")).to_be_visible()
    expect(page.locator("button:text('PDF')")).to_be_visible()

    page.screenshot(path="verification/liquidity_export.png")
    print("Liquidity page verified.")

    # 4. Verify Users Page
    page.goto("http://localhost:8080/users")
    page.wait_for_selector("text=User Management")

    # Check for Export buttons
    expect(page.locator("button:text('CSV')")).to_be_visible()
    expect(page.locator("button:text('Excel')")).to_be_visible()
    expect(page.locator("button:text('PDF')")).to_be_visible()

    page.screenshot(path="verification/users_export.png")
    print("Users page verified.")

    # 5. Verify Audit Page
    page.goto("http://localhost:8080/audit")
    page.wait_for_selector("text=Audit Log")

    # Check for Export buttons
    expect(page.locator("button:text('CSV')")).to_be_visible()
    expect(page.locator("button:text('Excel')")).to_be_visible()
    expect(page.locator("button:text('PDF')")).to_be_visible()

    page.screenshot(path="verification/audit_export.png")
    print("Audit page verified.")

    # 6. Verify Logs Page
    page.goto("http://localhost:8080/logs")
    page.wait_for_selector("text=System Logs")

    # Check for Export buttons (inside error logs first)
    expect(page.locator("#errors-content button:text('CSV')")).to_be_visible()
    expect(page.locator("#errors-content button:text('Excel')")).to_be_visible()
    expect(page.locator("#errors-content button:text('PDF')")).to_be_visible()

    page.screenshot(path="verification/logs_export.png")
    print("Logs page verified.")

    # 7. Verify Customer Settings Page
    page.goto("http://localhost:8080/customer-settings")
    page.wait_for_selector("text=Customer Settings")

    # Check for Export buttons
    expect(page.locator("button:text('CSV')")).to_be_visible()
    expect(page.locator("button:text('Excel')")).to_be_visible()
    expect(page.locator("button:text('PDF')")).to_be_visible()

    page.screenshot(path="verification/customer_settings_export.png")
    print("Customer Settings page verified.")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
