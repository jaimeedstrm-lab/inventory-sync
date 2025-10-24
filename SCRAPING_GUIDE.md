# Guide: Adding Web Scraping Suppliers

This guide shows how to add suppliers that require web scraping (login to portal, scrape inventory tables).

## Template for Scraping Supplier

Create `suppliers/supplier_name.py`:

```python
"""Supplier integration via web scraping."""
from typing import List, Dict, Any
from playwright.sync_api import sync_playwright, Page, Browser
from suppliers.base import BaseSupplier


class SupplierNameSupplier(BaseSupplier):
    """Supplier integration via web scraping with Playwright."""

    def __init__(self, name: str, config: Dict[str, Any], status_mapping: Dict[str, int]):
        """Initialize supplier.

        Args:
            name: Supplier name
            config: Configuration with keys:
                - login_url: URL to login page
                - inventory_url: URL to inventory page
                - username: Login username
                - password: Login password
                - selectors: CSS selectors for elements
            status_mapping: Status to quantity mapping
        """
        super().__init__(name, config, status_mapping)

        self.login_url = config.get("login_url")
        self.inventory_url = config.get("inventory_url")
        self.username = config.get("username")
        self.password = config.get("password")
        self.selectors = config.get("selectors", {})

        self.playwright = None
        self.browser = None
        self.page = None

    def authenticate(self) -> bool:
        """Authenticate by logging into the supplier portal.

        Returns:
            True if authentication successful

        Raises:
            Exception: If authentication fails
        """
        try:
            # Launch browser
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=True)
            self.page = self.browser.new_page()

            # Navigate to login page
            print(f"  Navigating to login page...")
            self.page.goto(self.login_url, wait_until="networkidle")

            # Fill login form
            print(f"  Filling login credentials...")
            username_selector = self.selectors.get("username_field", "#username")
            password_selector = self.selectors.get("password_field", "#password")
            submit_selector = self.selectors.get("submit_button", "button[type='submit']")

            self.page.fill(username_selector, self.username)
            self.page.fill(password_selector, self.password)

            # Submit form
            print(f"  Submitting login form...")
            self.page.click(submit_selector)

            # Wait for navigation after login
            self.page.wait_for_load_state("networkidle")

            # Check if login was successful
            # Adjust this based on your supplier's portal
            if "login" in self.page.url.lower() or "error" in self.page.content().lower():
                raise Exception("Login failed - still on login page or error detected")

            print(f"  ✓ Login successful")
            self.authenticated = True
            return True

        except Exception as e:
            self.cleanup()
            raise Exception(f"Authentication failed: {str(e)}")

    def fetch_inventory(self) -> List[Dict[str, Any]]:
        """Fetch inventory by scraping the supplier portal.

        Returns:
            List of product dictionaries

        Raises:
            Exception: If fetching fails
        """
        if not self.authenticated or not self.page:
            raise Exception("Not authenticated. Call authenticate() first.")

        try:
            products = []

            # Navigate to inventory page
            print(f"  Navigating to inventory page...")
            self.page.goto(self.inventory_url, wait_until="networkidle")

            # Get inventory table
            table_selector = self.selectors.get("inventory_table", "table")

            # Wait for table to load
            self.page.wait_for_selector(table_selector, timeout=30000)

            # Extract table data
            print(f"  Extracting inventory data...")
            rows = self.page.query_selector_all(f"{table_selector} tbody tr")

            for row in rows:
                try:
                    # Extract data from row
                    # ADJUST THESE SELECTORS BASED ON YOUR SUPPLIER'S TABLE STRUCTURE
                    cells = row.query_selector_all("td")

                    if len(cells) < 3:
                        continue  # Skip invalid rows

                    # Example: assuming columns are [Product Code, EAN, Stock Status]
                    # ADJUST BASED ON ACTUAL TABLE STRUCTURE
                    sku = cells[0].inner_text().strip()
                    ean = cells[1].inner_text().strip()
                    status = cells[2].inner_text().strip()

                    # Normalize status to quantity
                    quantity = self.normalize_quantity(status)

                    product = {
                        "ean": ean if ean else None,
                        "sku": sku if sku else None,
                        "quantity": quantity,
                        "supplier_data": {
                            "raw_status": status
                        }
                    }

                    if self.validate_product_data(product):
                        products.append(product)

                except Exception as e:
                    # Skip rows that fail to parse
                    print(f"  ⚠️  Skipped row: {e}")
                    continue

            print(f"  ✓ Extracted {len(products)} products")
            return products

        except Exception as e:
            raise Exception(f"Failed to fetch inventory: {str(e)}")

    def cleanup(self):
        """Close browser and cleanup resources."""
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
```

## Configuration Example

Add to `config/suppliers.json`:

```json
{
  "name": "supplier_name",
  "type": "scraper",
  "enabled": true,
  "config": {
    "login_url": "https://supplier.com/login",
    "inventory_url": "https://supplier.com/inventory",
    "username": "your_username",
    "password": "your_password",
    "selectors": {
      "username_field": "#username",
      "password_field": "#password",
      "submit_button": "button[type='submit']",
      "inventory_table": "table.inventory-table"
    }
  }
}
```

## Finding CSS Selectors

Use browser DevTools to find the correct selectors:

1. Open supplier portal in Chrome/Firefox
2. Right-click on element → "Inspect"
3. In DevTools, right-click on HTML element → Copy → Copy selector
4. Test selector in console: `document.querySelector("your-selector")`

### Common Selector Patterns

```css
/* By ID */
#username
#password
#loginButton

/* By class */
.form-control
.btn-login
.inventory-table

/* By attribute */
input[name="username"]
input[type="password"]
button[type="submit"]

/* By combination */
form.login-form input[name="username"]
table.data-table tbody tr td
```

## Handling CAPTCHA

If supplier has CAPTCHA:

```python
def authenticate(self) -> bool:
    # ... login code ...

    # Check for CAPTCHA
    if self.page.query_selector(".captcha-container"):
        raise Exception("CAPTCHA detected - manual intervention required")

    # ... continue ...
```

## Handling Pagination

If inventory spans multiple pages:

```python
def fetch_inventory(self) -> List[Dict[str, Any]]:
    products = []
    page_num = 1

    while True:
        # Extract products from current page
        page_products = self._extract_products_from_page()
        products.extend(page_products)

        # Check for next page button
        next_button = self.page.query_selector(".next-page")
        if not next_button or "disabled" in next_button.get_attribute("class"):
            break  # No more pages

        # Click next page
        next_button.click()
        self.page.wait_for_load_state("networkidle")
        page_num += 1

    return products
```

## Handling JavaScript-Heavy Sites

For sites that load data via JavaScript:

```python
# Wait for specific element to appear
self.page.wait_for_selector(".inventory-loaded", timeout=30000)

# Wait for network to be idle
self.page.wait_for_load_state("networkidle")

# Execute JavaScript to get data
data = self.page.evaluate("""
    () => {
        return window.inventoryData || [];
    }
""")
```

## Testing Your Scraper

```bash
# Test with dry-run mode
python main.py --supplier your_supplier --dry-run

# Check logs
cat logs/$(ls -t logs/ | head -1)
```

## Common Issues

### Issue: "Element not found"
**Solution**: Wait for element to load
```python
self.page.wait_for_selector("table", timeout=30000)
```

### Issue: "Wrong data extracted"
**Solution**: Inspect table structure and adjust column indices
```python
# Print table structure for debugging
html = self.page.query_selector("table").inner_html()
print(html)
```

### Issue: "Login fails silently"
**Solution**: Add screenshot for debugging
```python
self.page.screenshot(path="debug_login.png")
```

### Issue: "Cloudflare protection"
**Solution**: Use stealth mode
```python
context = self.browser.new_context(
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
)
self.page = context.new_page()
```

## Example: Real Table Structure

If your supplier's table looks like:

```html
<table class="inventory">
  <thead>
    <tr>
      <th>Varenr</th>
      <th>EAN</th>
      <th>Navn</th>
      <th>Lager</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>SKU-001</td>
      <td>5901234567890</td>
      <td>Product Name</td>
      <td>På lager</td>
    </tr>
  </tbody>
</table>
```

Extract like this:

```python
cells = row.query_selector_all("td")
sku = cells[0].inner_text().strip()     # Varenr
ean = cells[1].inner_text().strip()     # EAN
name = cells[2].inner_text().strip()    # Navn
status = cells[3].inner_text().strip()  # Lager
```

## Need Help?

If you need help adding a specific supplier, provide:
1. Supplier portal URL
2. Screenshot of login page
3. Screenshot of inventory page
4. Table structure (HTML from DevTools)

I can help create a custom scraper implementation.
