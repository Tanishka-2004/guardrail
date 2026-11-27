import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path(r"C:\Users\tmmud\.gemini\antigravity\scratch\guardrail\screenshots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "http://localhost:3000"

def capture_all():
    print(f"Launching Chrome from: {CHROME_PATH}")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=True,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(
            viewport={"width": 1600, "height": 950},
            device_scale_factor=1.5
        )
        page = context.new_page()

        # 1. Login Page
        print("Capturing 1: Login Page...")
        page.goto(f"{BASE_URL}/login")
        page.wait_for_selector("input[type='email']")
        time.sleep(1.5)
        login_img = OUTPUT_DIR / "01_login_page.png"
        page.screenshot(path=str(login_img), full_page=False)
        print(f"Saved: {login_img}")

        # Perform Login using Administrator demo button
        print("Logging in as Administrator...")
        admin_btn = page.locator("button:has-text('Administrator')")
        if admin_btn.count() > 0:
            admin_btn.first.click()
            time.sleep(0.5)
        else:
            page.fill("input[type='email']", "admin@guardrail.io")
            page.fill("input[type='password']", "Password123!")
            
        page.click("button[type='submit']")
        
        # Wait for navigation to Dashboard
        page.wait_for_url(f"{BASE_URL}/", timeout=10000)
        time.sleep(3)  # Let charts and metrics settle

        # 2. Operations Dashboard
        print("Capturing 2: Operations Dashboard...")
        dashboard_img = OUTPUT_DIR / "02_operations_dashboard.png"
        page.screenshot(path=str(dashboard_img), full_page=False)
        print(f"Saved: {dashboard_img}")

        # 3. Live Alert Queue
        print("Capturing 3: Live Alert Queue...")
        page.goto(f"{BASE_URL}/queue")
        page.wait_for_selector("table", timeout=10000)
        time.sleep(2.5)
        queue_img = OUTPUT_DIR / "03_live_triage_queue.png"
        page.screenshot(path=str(queue_img), full_page=False)
        print(f"Saved: {queue_img}")

        # 4. Alert Investigation Drawer (Click first row / View button)
        print("Capturing 4: Alert Investigation Drawer...")
        # Click the first row to open drawer
        first_row = page.locator("tbody tr").first
        if first_row.count() > 0:
            first_row.click()
            time.sleep(2.5)  # Wait for drawer animation and data fetch
            drawer_img = OUTPUT_DIR / "04_alert_investigation_drawer.png"
            page.screenshot(path=str(drawer_img), full_page=False)
            print(f"Saved: {drawer_img}")
            
            # Close drawer
            page.keyboard.press("Escape")
            time.sleep(0.5)

        # 5. Analyst Workload & Capacity Table
        print("Capturing 5: Analyst Workload & Capacity...")
        page.goto(f"{BASE_URL}/workload")
        page.wait_for_selector("table", timeout=10000)
        time.sleep(2)
        workload_img = OUTPUT_DIR / "05_analyst_workload.png"
        page.screenshot(path=str(workload_img), full_page=False)
        print(f"Saved: {workload_img}")

        # 6. Dead Letter Queue Management
        print("Capturing 6: Dead Letter Queue (DLQ)...")
        page.goto(f"{BASE_URL}/dlq")
        page.wait_for_selector("table", timeout=10000)
        time.sleep(2)
        dlq_img = OUTPUT_DIR / "06_dead_letter_queue.png"
        page.screenshot(path=str(dlq_img), full_page=False)
        print(f"Saved: {dlq_img}")

        # 7. System Health & Observability
        print("Capturing 7: System Health & Observability...")
        page.goto(f"{BASE_URL}/system")
        time.sleep(2)
        system_img = OUTPUT_DIR / "07_system_health.png"
        page.screenshot(path=str(system_img), full_page=False)
        print(f"Saved: {system_img}")

        browser.close()
        print("All high-fidelity screenshots successfully captured!")

if __name__ == "__main__":
    capture_all()
