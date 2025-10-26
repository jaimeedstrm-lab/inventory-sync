"""Response Nordic supplier integration via web scraping."""
import re
from typing import List, Dict, Any
from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeout
from suppliers.base import BaseSupplier


class ResponseNordicSupplier(BaseSupplier):
    """Supplier integration for Response Nordic via web scraping with EAN search."""

    def __init__(self, name: str, config: Dict[str, Any], status_mapping: Dict[str, int], headless: bool = True):
        """Initialize Response Nordic supplier.

        Args:
            name: Supplier name
            config: Configuration with keys:
                - base_url: Base website URL
                - username: Login username (email)
                - password: Login password
            status_mapping: Status to quantity mapping
            headless: Run browser in headless mode (default True)
        """
        super().__init__(name, config, status_mapping)

        self.base_url = config.get("base_url", "https://active.response-nordic.no")
        self.username = config.get("username")
        self.password = config.get("password")
        self.headless = headless

        self.playwright = None
        self.browser = None
        self.page = None

    def authenticate(self) -> bool:
        """Authenticate with Response Nordic website.

        Returns:
            True if authentication successful

        Raises:
            Exception: If authentication fails
        """
        try:
            print(f"  Starting browser...")
            self.playwright = sync_playwright().start()

            # Launch browser
            self.browser = self.playwright.chromium.launch(headless=self.headless)
            self.page = self.browser.new_page()

            # Take screenshot on error for debugging
            if not self.headless:
                print(f"  Running in visible mode for debugging")

            # Set timeout
            self.page.set_default_timeout(60000)  # 60 seconds

            print(f"  Navigating to {self.base_url}...")
            self.page.goto(self.base_url, wait_until="domcontentloaded")

            # Wait a bit for page to fully load
            self.page.wait_for_timeout(2000)

            # Click the "Forhandler logg inn" button in header
            print(f"  Opening login popup...")
            login_button = self.page.locator('a#loginout.LogInButton[href="#login"]').first
            login_button.wait_for(state="visible", timeout=5000)
            login_button.click()

            # Wait for login form to appear
            print(f"  Waiting for login form...")
            self.page.wait_for_timeout(1500)

            # Wait for form fields to be visible
            self.page.wait_for_selector('input[type="email"]#username[name="email"]', state="visible", timeout=10000)

            # Fill in credentials
            print(f"  Entering credentials...")

            # Fill email (username)
            email_field = self.page.locator('input[type="email"]#username[name="email"]').first
            email_field.fill(self.username)
            print(f"    ✓ Email filled")

            # Fill password
            password_field = self.page.locator('input[type="password"]#password[name="password"]').first
            password_field.fill(self.password)
            print(f"    ✓ Password filled")

            # Click login button
            print(f"  Submitting login form...")
            # The button has onclick="mcWeb.login.login();"
            submit_button = self.page.locator('button.login-btn[onclick*="mcWeb.login.login"]').first
            submit_button.click()

            # Wait for login to complete
            print(f"  Verifying login...")
            try:
                # Wait for page to reload or some indicator of successful login
                self.page.wait_for_timeout(3000)  # Wait 3 seconds for login to process

                # Check if we're logged in by looking for the login button changing
                # or by checking if we can still see the login form
                try:
                    # If we still see the login form, login failed
                    login_form_still_visible = self.page.locator('input[type="email"]#username').is_visible()
                    if login_form_still_visible:
                        raise Exception("Login form still visible - login may have failed")
                except:
                    # Login form not visible anymore - good sign
                    pass

                print(f"  ✓ Login successful")
                self.authenticated = True
                return True

            except Exception as e:
                raise Exception(f"Could not verify successful login: {str(e)}")

        except Exception as e:
            self.cleanup()
            raise Exception(f"Authentication failed: {str(e)}")

    def search_product_by_ean(self, ean: str) -> Dict[str, Any]:
        """Search for a product by EAN and scrape its data.

        Args:
            ean: EAN code to search for

        Returns:
            Product dictionary with quantity and data, or None if not found
        """
        if not self.authenticated or not self.page:
            raise Exception("Not authenticated. Call authenticate() first.")

        try:
            # Find the search input field with multiple fallback selectors
            search_box = None

            # Try multiple selectors for the search box
            selectors_to_try = [
                'input[name="ctl00$Search1$SearchBox$InstSearchTB"]',
                'input#ctl00_Search1_SearchBox_InstSearchTB',
                'input[type="search"].main-search-type',
                'input[type="search"][autocomplete="off"]',
                'input[placeholder="Search"]'
            ]

            for selector in selectors_to_try:
                try:
                    search_box = self.page.locator(selector).first
                    search_box.wait_for(state="visible", timeout=3000)
                    print(f"  Found search box with selector: {selector}")
                    break
                except:
                    continue

            if not search_box:
                raise Exception("Could not find search box with any known selector")

            # Clear search box completely first
            search_box.click()
            search_box.fill("")
            self.page.wait_for_timeout(500)

            # Close any existing instant search popup by pressing Escape
            try:
                search_box.press("Escape")
                self.page.wait_for_timeout(300)
            except:
                pass

            # Type character by character to trigger instant search
            # Slower typing to ensure instant search triggers properly
            search_box.type(ean, delay=200)
            print(f"  Typed EAN: {ean}")

            # Wait even longer for instant search results popup to appear
            print(f"  Waiting for instant search results...")
            self.page.wait_for_timeout(5000)  # Increased to 5 seconds

            # Look for product link in instant search popup
            product_link = self.page.locator('a.NoUnderLine[data-bind*="ProduktLink"]').first

            try:
                # Wait for the link to be visible with much longer timeout
                product_link.wait_for(state="visible", timeout=10000)  # Increased to 10 seconds
                print(f"  ✓ Found product in instant search preview")

                # Click the first/only product link
                product_link.click()
                print(f"  Clicked on product link")

                # Wait for product page to load
                self.page.wait_for_load_state("domcontentloaded", timeout=15000)
                self.page.wait_for_timeout(1500)
                print(f"  Product page loaded: {self.page.url}")

            except PlaywrightTimeout:
                # Instant search didn't show results - product might not exist in supplier's inventory
                print(f"  ✗ No instant search results found for EAN: {ean}")
                # Product not found in supplier's inventory - return None (will show as 0 in Shopify)
                return None

            # Scrape and verify product data from the product page
            product_data = self._scrape_product_page(ean)
            return product_data

        except PlaywrightTimeout:
            # Product not found or timeout
            return None
        except Exception as e:
            print(f"  Warning: Error searching for EAN {ean}: {str(e)}")
            return None

    def _scrape_product_page(self, ean: str) -> Dict[str, Any]:
        """Scrape product data from current product page.

        Args:
            ean: EAN to verify

        Returns:
            Product dictionary
        """
        # Verify EAN matches
        try:
            ean_element = self.page.locator('span.ean-number').first
            ean_on_page = ean_element.inner_text().strip()

            if ean_on_page != ean:
                raise Exception(f"EAN mismatch on product page: expected {ean}, found {ean_on_page}")
        except Exception as e:
            raise Exception(f"Could not verify EAN on product page: {str(e)}")

        # Get SKU (product number)
        sku = None
        try:
            sku_element = self.page.locator('span.prd-num-label').first
            sku = sku_element.inner_text().strip()
        except:
            pass

        # Get stock status
        quantity = 0
        raw_status = None

        try:
            # Check the stock container
            stock_div = self.page.locator('div.product-stock div.main-warehouse').first

            if stock_div.is_visible():
                stock_html = stock_div.inner_html()
                stock_text = stock_div.inner_text()
                raw_status = stock_text.strip()

                # Check which stock icon is present
                if 'in-stock2.png' in stock_html:
                    # In stock - extract quantity
                    # Format: "<span>20+</span><span>på lager</span>"
                    qty_match = re.search(r'<span>(\d+)\+?</span>', stock_html)
                    if qty_match:
                        quantity = int(qty_match.group(1))
                    else:
                        # Default to some quantity if we see in-stock icon
                        quantity = self.normalize_quantity("på lager")

                elif 'no-stock2.png' in stock_html:
                    # Not in stock
                    quantity = 0
                    raw_status = "Ikke på lager"

                elif 'stock-orange.png' in stock_html:
                    # Expected in stock (future date) - treat as out of stock for now
                    quantity = 0
                    # Extract expected date if needed
                    date_match = re.search(r'<span>Forventet til lager </span><span>([\d.]+)</span>', stock_html)
                    if date_match:
                        expected_date = date_match.group(1)
                        raw_status = f"Forventet til lager {expected_date}"
                    else:
                        raw_status = "Forventet til lager"

                else:
                    # Unknown status - try to normalize from text
                    quantity = self.normalize_quantity(stock_text)

        except Exception as e:
            print(f"  Warning: Could not parse stock status: {str(e)}")
            quantity = 0
            raw_status = "Unknown"

        # Get product title
        title = None
        try:
            title_element = self.page.locator('h1').first
            title = title_element.inner_text().strip()
        except:
            pass

        return {
            "ean": ean,
            "sku": sku,
            "quantity": quantity,
            "raw_status": raw_status,
            "supplier_data": {
                "title": title,
                "article_number": sku,
                "url": self.page.url
            }
        }

    def fetch_inventory(self) -> List[Dict[str, Any]]:
        """Fetch inventory from Response Nordic by searching for EANs.

        This method expects to receive EANs to search for.
        Since we need the EAN list from Shopify, this is handled differently.

        Returns:
            Empty list (actual fetching happens via search_products_by_ean)
        """
        # This supplier works differently - we search individual EANs
        # The main sync logic will call search_product_by_ean for each EAN
        return []

    def search_products_by_ean_list(self, ean_list: List[str]) -> List[Dict[str, Any]]:
        """Search for multiple products by EAN.

        Args:
            ean_list: List of EAN codes to search for

        Returns:
            List of found products with inventory data
        """
        if not self.authenticated:
            raise Exception("Not authenticated. Call authenticate() first.")

        products = []
        total = len(ean_list)

        print(f"  Searching for {total} products...")

        for i, ean in enumerate(ean_list, 1):
            if i % 10 == 0 or i == total:
                print(f"  Progress: {i}/{total} products searched...")

            product = self.search_product_by_ean(ean)

            if product and self.validate_product_data(product):
                products.append(product)

            # Small delay to avoid overwhelming the server
            if i < total:
                self.page.wait_for_timeout(500)  # 500ms delay between searches

        return products

    def cleanup(self):
        """Close browser and cleanup resources."""
        try:
            if self.page:
                self.page.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except:
            pass
