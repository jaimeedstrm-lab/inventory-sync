#!/usr/bin/env python3
"""Script to refresh Petcare cookies by logging in and saving the session."""

import json
import os
from playwright.sync_api import sync_playwright
import time

def refresh_petcare_cookies():
    """Login to Petcare and save fresh cookies."""

    # Load credentials from config
    config_path = "config/suppliers.json"
    if not os.path.exists(config_path):
        print("❌ Config file not found. Please ensure config/suppliers.json exists.")
        return False

    with open(config_path, 'r') as f:
        config = json.load(f)

    # Find Petcare config
    petcare_config = None
    for supplier in config.get("suppliers", []):
        if supplier.get("name") == "petcare":
            petcare_config = supplier
            break

    if not petcare_config:
        print("❌ Petcare config not found in suppliers.json")
        return False

    # Get config object
    config_obj = petcare_config.get("config", {})
    username = config_obj.get("username")
    password = config_obj.get("password")
    base_url = config_obj.get("base_url", "https://www.petcare.se")

    if not username or not password:
        print("❌ Petcare username or password not found in config")
        return False

    print("🌐 Starting browser...")
    print(f"   Username: {username}")
    print(f"   Base URL: {base_url}")

    with sync_playwright() as p:
        # Launch browser in NON-headless mode so you can solve reCAPTCHA
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print("\n📍 Navigating to Petcare login page...")
        page.goto(f"{base_url}/mitt-konto/", wait_until="networkidle")

        # Wait a bit for page to load
        time.sleep(2)

        print("\n🔐 Entering credentials...")

        # Fill username
        username_field = page.locator('input#username').first
        username_field.fill(username)
        print("   ✓ Username filled")

        # Fill password
        password_field = page.locator('input#password').first
        password_field.fill(password)
        print("   ✓ Password filled")

        # Click login button
        print("\n🤖 Clicking login button...")
        login_button = page.locator('button[name="login"]').first
        login_button.click()

        print("\n⚠️  IMPORTANT: If reCAPTCHA appears, please solve it manually!")
        print("   After successful login, press ENTER in this terminal to continue...")
        input()

        # Verify login was successful
        print("\n🔍 Verifying login...")
        current_url = page.url

        if "mitt-konto" in current_url and "login" not in current_url.lower():
            print("   ✓ Login appears successful!")
        else:
            print(f"   ⚠️  Not sure if login succeeded. Current URL: {current_url}")
            print("   If you're logged in, press ENTER to continue. Otherwise, press Ctrl+C to cancel.")
            input()

        # Save cookies
        print("\n💾 Saving cookies...")
        cookies = context.cookies()

        # Ensure cookies directory exists
        os.makedirs("cookies", exist_ok=True)

        # Save to file
        cookie_file = "cookies/petcare_cookies.json"
        with open(cookie_file, 'w') as f:
            json.dump(cookies, f, indent=2)

        print(f"   ✓ Cookies saved to {cookie_file}")
        print(f"   ✓ Total cookies: {len(cookies)}")

        # Show important cookies
        print("\n📋 Important cookies saved:")
        for cookie in cookies:
            if 'wordpress_logged_in' in cookie['name'] or 'wordpress_sec' in cookie['name']:
                expires = cookie.get('expires', -1)
                if expires > 0:
                    import datetime
                    expire_date = datetime.datetime.fromtimestamp(expires)
                    print(f"   - {cookie['name'][:30]}... expires: {expire_date}")
                else:
                    print(f"   - {cookie['name'][:30]}... (session cookie)")

        print("\n✅ Done! You can now close the browser.")
        print("\n📝 Next steps:")
        print("   1. Copy the contents of cookies/petcare_cookies.json")
        print("   2. Update the PETCARE_COOKIES secret in GitHub:")
        print("      - Go to: https://github.com/jaimeedstrm-lab/inventory-sync/settings/secrets/actions")
        print("      - Edit PETCARE_COOKIES secret")
        print("      - Paste the new cookie content")

        # Wait a bit before closing
        time.sleep(3)
        browser.close()

    return True

if __name__ == "__main__":
    print("=" * 60)
    print("Petcare Cookie Refresh Tool")
    print("=" * 60)

    success = refresh_petcare_cookies()

    if success:
        print("\n" + "=" * 60)
        print("✅ SUCCESS!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ FAILED")
        print("=" * 60)
