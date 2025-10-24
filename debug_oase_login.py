#!/usr/bin/env python3
"""Debug Oase Outdoors authentication flow."""
import requests

username = "emil@natursortimentet.se"
password = "Norrsken25"

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
})

print("=" * 80)
print("OASE OUTDOORS AUTHENTICATION DEBUG")
print("=" * 80)
print()

# Step 1: Access the portal
print("Step 1: Accessing dealer portal...")
portal_url = "https://www.oase-outdoors.dk/en-gb/dealernet"

try:
    r = session.get(portal_url, timeout=30)
    print(f"Status: {r.status_code}")
    print(f"Final URL: {r.url}")
    print(f"Cookies: {dict(session.cookies)}")
    print()
except Exception as e:
    print(f"Error: {e}\n")

# Step 2: Try different login endpoints
login_urls = [
    "https://www.oase-outdoors.dk/Admin/Public/ExtranetLogOnMasterPage.aspx",
    "https://www.oase-outdoors.dk/Admin/Public/ExtranetLogon.aspx",
]

for login_url in login_urls:
    print(f"Step 2: Trying login at {login_url}")

    login_data = {
        "ID": username,
        "Password": password,
        "Username": username,
        "password": password,
        "LoginAction": "Login",
        "AutoLogin": "0"
    }

    try:
        r = session.post(login_url, data=login_data, allow_redirects=True, timeout=30)
        print(f"  Status: {r.status_code}")
        print(f"  Final URL: {r.url}")
        print(f"  Cookies: {dict(session.cookies)}")

        # Check if still on login page
        if "login" not in r.url.lower():
            print(f"  ✓ Not on login page anymore - might be logged in!")
        print()
    except Exception as e:
        print(f"  Error: {e}\n")

# Step 3: Try to access API
print("Step 3: Testing API access...")
api_url = "https://www.oase-outdoors.dk/apiv2/common/shopping/items/en-GB/dealernet-order"

# Try without parameters
try:
    r = session.get(api_url, timeout=30)
    print(f"Without params - Status: {r.status_code}")
    if r.status_code == 200:
        print(f"  Response length: {len(r.text)}")
        print(f"  Preview: {r.text[:500]}")
    else:
        print(f"  Error response: {r.text[:200]}")
    print()
except Exception as e:
    print(f"Error: {e}\n")

# Try with PageSize parameter
try:
    r = session.get(api_url, params={"PageSize": 10}, timeout=30)
    print(f"With PageSize=10 - Status: {r.status_code}")
    if r.status_code == 200:
        print(f"  Response length: {len(r.text)}")
        print(f"  Preview: {r.text[:500]}")
    else:
        print(f"  Error response: {r.text[:200]}")
    print()
except Exception as e:
    print(f"Error: {e}\n")

# Step 4: Try accessing the dealernet page after login
print("Step 4: Accessing dealernet page after login...")
try:
    r = session.get(portal_url, timeout=30)
    print(f"Status: {r.status_code}")
    print(f"Final URL: {r.url}")

    # Check if we're logged in by looking for logout link or user info
    if "logout" in r.text.lower() or "log out" in r.text.lower():
        print("✓ Found logout link - WE ARE LOGGED IN!")
    else:
        print("✗ No logout link found - might not be logged in")
    print()
except Exception as e:
    print(f"Error: {e}\n")

# Step 5: Try API again after confirming login
print("Step 5: Trying API again...")
try:
    r = session.get(api_url, timeout=30)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        try:
            data = r.json()
            if isinstance(data, list):
                print(f"✓✓ SUCCESS! Got {len(data)} items")
                if data:
                    print(f"First item keys: {list(data[0].keys())}")
                    print(f"First item sample: {data[0]}")
            elif isinstance(data, dict):
                print(f"✓✓ SUCCESS! Got dict with keys: {list(data.keys())}")
                print(f"Sample: {data}")
        except:
            print(f"Response is not JSON: {r.text[:300]}")
    else:
        print(f"Error: {r.status_code}")
        print(f"Response: {r.text[:300]}")
except Exception as e:
    print(f"Error: {e}")

print()
print("=" * 80)
print("Debug complete! Please review the output above.")
print("=" * 80)
