#!/usr/bin/env python3
"""Test script for Oase Outdoors dealer portal authentication."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

username = os.getenv("OASE_USERNAME")
password = os.getenv("OASE_PASSWORD")

print("=" * 60)
print("Oase Outdoors Dealer Portal Test")
print("=" * 60)
print()

if not username or not password:
    print("❌ Missing credentials!")
    print("Please set OASE_USERNAME and OASE_PASSWORD in .env")
    exit(1)

print(f"Username: {username}")
print(f"Password: {'*' * len(password)}")
print()

session = requests.Session()

# Step 1: Try to access the dealer portal login page
portal_url = "https://www.oase-outdoors.dk/en-gb/dealernet"

print(f"Step 1: Accessing portal at {portal_url}")
try:
    response = session.get(portal_url, timeout=10)
    print(f"  Status: {response.status_code}")
    print(f"  Cookies received: {list(session.cookies.keys())}")
    print()
except Exception as e:
    print(f"  Error: {e}")
    print()

# Step 2: Try common Dynamicweb login endpoints
login_endpoints = [
    "https://www.oase-outdoors.dk/Admin/Public/ExtranetLogon.aspx",
    "https://www.oase-outdoors.dk/Admin/Public/ExtranetLogOnMasterPage.aspx",
    "https://www.oase-outdoors.dk/en-gb/dealernet/login",
    "https://www.oase-outdoors.dk/dwapi/users/login",
    "https://www.oase-outdoors.dk/api/login"
]

print("Step 2: Testing login endpoints...")
print()

for login_url in login_endpoints:
    print(f"Trying: {login_url}")

    # Try POST with form data (common for Dynamicweb)
    try:
        response = session.post(
            login_url,
            data={
                "username": username,
                "password": password,
                "Username": username,  # Sometimes capitalized
                "Password": password,
                "ID": username,
                "LoginBtn": "Log in"
            },
            allow_redirects=True,
            timeout=10
        )
        print(f"  Form POST: {response.status_code}")
        print(f"  Final URL: {response.url}")
        print(f"  Cookies: {list(session.cookies.keys())}")

        if response.status_code == 200 and "login" not in response.url.lower():
            print(f"  ✓ Might have logged in! Let's test API access...")

            # Try to access API endpoints
            api_endpoints = [
                "https://www.oase-outdoors.dk/dwapi/content/products",
                "https://www.oase-outdoors.dk/dwapi/ecom/products",
                "https://www.oase-outdoors.dk/api/products",
                "https://www.oase-outdoors.dk/en-gb/dealernet/api/products"
            ]

            for api_url in api_endpoints:
                try:
                    api_response = session.get(api_url, timeout=10)
                    print(f"    API {api_url}: {api_response.status_code}")
                    if api_response.status_code == 200:
                        print(f"    ✓✓ API WORKS! Preview:")
                        print(f"    {api_response.text[:300]}")
                except Exception as e:
                    print(f"    API error: {e}")

        print()
    except Exception as e:
        print(f"  Error: {e}")
        print()

# Step 3: Try JSON-based login
print("Step 3: Testing JSON-based authentication...")
print()

json_login_url = "https://www.oase-outdoors.dk/dwapi/users/login"
try:
    response = session.post(
        json_login_url,
        json={
            "username": username,
            "password": password
        },
        timeout=10
    )
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.text[:200]}")
    print(f"  Cookies: {list(session.cookies.keys())}")
except Exception as e:
    print(f"  Error: {e}")

print()
print("=" * 60)
print("Test complete!")
print("=" * 60)
print()
print("What worked? Please share the output above.")
print("Also, can you tell me:")
print("1. What API endpoint did you discover in DevTools?")
print("2. What was the exact URL path for the product/inventory data?")
