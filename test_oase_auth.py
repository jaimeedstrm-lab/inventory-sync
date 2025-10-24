#!/usr/bin/env python3
"""Helper script to test Oase Outdoors authentication."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

base_url = os.getenv("OASE_BASE_URL", "").rstrip("/")
username = os.getenv("OASE_USERNAME")
password = os.getenv("OASE_PASSWORD")

print("=" * 60)
print("Oase Outdoors Authentication Test")
print("=" * 60)
print(f"\nBase URL: {base_url}")
print(f"Username: {username}")
print(f"Password: {'*' * len(password) if password else 'NOT SET'}")
print()

if not all([base_url, username, password]):
    print("❌ Missing credentials in .env file")
    print("\nPlease set:")
    print("  OASE_BASE_URL=https://...")
    print("  OASE_USERNAME=your_username")
    print("  OASE_PASSWORD=your_password")
    exit(1)

session = requests.Session()

# Test 1: Try common Dynamicweb login endpoints
print("Testing authentication methods...\n")

endpoints_to_try = [
    "/Admin/Public/ExtranetLogon.aspx",
    "/api/auth/login",
    "/api/login",
    "/extranet/login",
    "/dealer/login",
    "/login",
    "/api/token",
    "/DWExtranet/Login.aspx"
]

for endpoint in endpoints_to_try:
    url = f"{base_url}{endpoint}"
    print(f"Trying: {url}")

    try:
        # Method 1: POST with JSON
        response = session.post(
            url,
            json={"username": username, "password": password},
            timeout=10,
            allow_redirects=False
        )
        print(f"  JSON POST: {response.status_code}")
        if response.status_code in [200, 302]:
            print(f"  ✓ Might work! Cookies: {dict(session.cookies)}")
            if response.text:
                print(f"  Response preview: {response.text[:200]}")

        # Method 2: POST with form data
        response = session.post(
            url,
            data={"username": username, "password": password},
            timeout=10,
            allow_redirects=False
        )
        print(f"  Form POST: {response.status_code}")
        if response.status_code in [200, 302]:
            print(f"  ✓ Might work! Cookies: {dict(session.cookies)}")

    except requests.exceptions.RequestException as e:
        print(f"  Error: {e}")

    print()

# Test 2: Try to access common API endpoints without auth
print("\nTesting API endpoints (without auth)...\n")

api_endpoints = [
    "/api/products",
    "/api/inventory",
    "/api/stock",
    "/webapi/products",
    "/dwapi/products"
]

for endpoint in api_endpoints:
    url = f"{base_url}{endpoint}"
    print(f"Trying: {url}")

    try:
        response = session.get(url, timeout=10)
        print(f"  Status: {response.status_code}")
        if response.status_code == 401:
            print(f"  → Needs authentication (good sign!)")
        elif response.status_code == 200:
            print(f"  ✓ Accessible! Preview: {response.text[:200]}")
    except requests.exceptions.RequestException as e:
        print(f"  Error: {e}")

    print()

# Test 3: Try basic auth
print("\nTesting Basic Authentication...\n")

session.auth = (username, password)

for endpoint in api_endpoints:
    url = f"{base_url}{endpoint}"
    print(f"Trying: {url}")

    try:
        response = session.get(url, timeout=10)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            print(f"  ✓ Basic auth works! Preview: {response.text[:200]}")
    except requests.exceptions.RequestException as e:
        print(f"  Error: {e}")

    print()

print("=" * 60)
print("Testing complete!")
print("=" * 60)
print("\nPlease review the results above and let me know which method worked.")
