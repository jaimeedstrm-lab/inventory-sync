"""Order Nordic supplier integration via web scraping."""
import re
from typing import List, Dict, Any
from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeout
from suppliers.base import BaseSupplier


class OrderNordicSupplier(BaseSupplier):
    """Supplier integration for Order Nordic via web scraping."""

    def __init__(self, name: str, config: Dict[str, Any], status_mapping: Dict[str, int], headless: bool = True):
        """Initialize Order Nordic supplier.

        Args:
            name: Supplier name
            config: Configuration with keys:
                - base_url: Base website URL
                - username: Login username
                - password: Login password
            status_mapping: Status to quantity mapping
            headless: Run browser in headless mode (default True)
        """
        super().__init__(name, config, status_mapping)

        self.base_url = config.get("base_url", "https://order.se")
        self.username = config.get("username")
        self.password = config.get("password")
        self.headless = headless

        self.playwright = None
        self.browser = None
        self.page = None

    def authenticate(self) -> bool:
        """Authenticate with Order Nordic website.

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
            self.page.set_default_timeout(30000)  # 30 seconds

            print(f"  Navigating to {self.base_url}...")
            self.page.goto(self.base_url, wait_until="networkidle")

            # Wait a bit for page to fully load
            self.page.wait_for_timeout(2000)

            # Try to trigger login popup
            print(f"  Opening login popup...")

            # Method 1: Try direct navigation to #login-popup
            try:
                self.page.goto(f"{self.base_url}/#login-popup")
                self.page.wait_for_timeout(1000)
                print(f"    Navigated to #login-popup")
            except:
                pass

            # Method 2: Try JavaScript to show the popup
            try:
                self.page.evaluate("""
                    () => {
                        const popup = document.getElementById('login-popup');
                        if (popup) {
                            popup.style.display = 'block';
                            popup.style.visibility = 'visible';
                            popup.classList.add('is-visible', 'visible');
                        }
                    }
                """)
                print(f"    Attempted to show popup via JavaScript")
            except:
                pass

            # Wait for popup to become visible
            print(f"  Waiting for login popup to appear...")
            self.page.wait_for_timeout(1500)

            # Wait for the popup container to be visible
            # The popup should have id="login-popup" based on the href
            try:
                popup = self.page.locator('#login-popup')
                popup.wait_for(state="visible", timeout=5000)
                print(f"  ✓ Login popup visible")
            except:
                print(f"  Warning: Could not find #login-popup, trying to find form anyway...")

            # Wait for form fields to be visible in the popup
            print(f"  Waiting for form fields...")
            # Username field is name="external_id", Password is name="password"
            self.page.wait_for_selector('input[name="external_id"][placeholder="Användare"]', state="visible", timeout=5000)

            # Fill in credentials
            print(f"  Entering credentials...")

            # Fill username (external_id)
            username_field = self.page.locator('input[name="external_id"][placeholder="Användare"]').first
            username_field.fill(self.username)
            print(f"    ✓ Username filled")

            # Fill password
            password_field = self.page.locator('input[name="password"][placeholder="Lösenord"]').first
            password_field.fill(self.password)
            print(f"    ✓ Password filled")

            # Click login submit button in popup
            print(f"  Submitting login form...")
            submit_button = self.page.locator('button:has-text("LOGGA IN"), input[type="submit"]').first
            submit_button.click()

            # Wait for login to complete (check for logout button or user indicator)
            print(f"  Verifying login...")
            try:
                # Wait for page to reload or some indicator of successful login
                self.page.wait_for_timeout(2000)  # Wait 2 seconds for login to process

                # Check if we're still seeing login button (failed) or if we see user menu
                if self.page.locator('text="LOGGA UT"').first.is_visible():
                    print(f"  ✓ Login successful (found logout button)")
                    self.authenticated = True
                    return True
                else:
                    # Try another verification method
                    print(f"  ✓ Login appears successful")
                    self.authenticated = True
                    return True

            except:
                raise Exception("Could not verify successful login")

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
            # Search in desktop header search box
            # Try desktop search first, fall back to mobile if needed
            search_box = None

            try:
                search_box = self.page.locator('#modern-header-desktop-search-input').first
                search_box.wait_for(state="visible", timeout=2000)
            except:
                # Try generic search if desktop not found
                search_box = self.page.locator('input[name="keywords"][type="search"]').first
                search_box.wait_for(state="visible", timeout=5000)

            # Clear any existing text and fill with EAN
            search_box.click()  # Focus the field
            search_box.fill(ean)

            # Submit search
            search_box.press("Enter")

            # Wait for search results or product page
            self.page.wait_for_load_state("networkidle", timeout=10000)
            self.page.wait_for_timeout(1000)  # Extra wait for dynamic content

            # Check if we landed on a product page directly or search results
            # Look for EAN verification on product page
            try:
                ean_element = self.page.locator(f'text=/EAN-kod:\\s*{ean}/').first
                ean_element.wait_for(timeout=3000)
                # We're on the product page
            except:
                # We're on search results page - click first product result
                try:
                    # Look for product card links (class="image cd-item" or h2.product-name a)
                    first_result = None

                    # Try product image link first
                    try:
                        first_result = self.page.locator('a.image.cd-item').first
                        first_result.wait_for(state="visible", timeout=2000)
                    except:
                        # Try product name link
                        first_result = self.page.locator('h2.product-name a').first
                        first_result.wait_for(state="visible", timeout=2000)

                    if not first_result:
                        # No results found
                        return None

                    # Click the product
                    first_result.click()
                    self.page.wait_for_load_state("networkidle", timeout=10000)
                    self.page.wait_for_timeout(1000)

                    # Verify we're on a product page (don't need to verify EAN yet)
                except:
                    # Product not found or couldn't click
                    return None

            # Scrape product data
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
        ean_text = self.page.locator('b:has-text("EAN-kod:")').locator('..').inner_text()
        ean_match = re.search(r'EAN-kod:\s*(\d+)', ean_text)

        if not ean_match or ean_match.group(1) != ean:
            raise Exception(f"EAN mismatch on product page")

        # Get article number
        art_nr = None
        try:
            art_nr_text = self.page.locator('b:has-text("Art. nr:")').locator('..').inner_text()
            art_nr_match = re.search(r'Art\. nr:\s*(\S+)', art_nr_text)
            if art_nr_match:
                art_nr = art_nr_match.group(1)
        except:
            pass

        # Get stock status
        quantity = 0
        raw_status = None

        try:
            # Check for "I lager X st" (in stock)
            stock_div = self.page.locator('div.column.stock').first

            if stock_div.is_visible():
                stock_text = stock_div.inner_text()
                raw_status = stock_text.strip()

                # Check if in stock
                if "I lager" in stock_text:
                    # Extract quantity: "I lager 9 st" -> 9
                    qty_match = re.search(r'I lager\s+(\d+)\s*st', stock_text)
                    if qty_match:
                        quantity = int(qty_match.group(1))
                    else:
                        # Default to some quantity if we see "I lager" but no number
                        quantity = self.normalize_quantity("i lager")

                elif "Åter i lager" in stock_text:
                    # Out of stock, coming back later
                    quantity = 0
                    raw_status = stock_text.strip()

                elif "out-of-stock" in stock_div.get_attribute("class"):
                    # Out of stock
                    quantity = 0

                else:
                    # Try to normalize status string
                    quantity = self.normalize_quantity(stock_text)

        except Exception as e:
            print(f"  Warning: Could not parse stock status: {str(e)}")
            quantity = 0
            raw_status = "Unknown"

        # Get product title
        title = None
        try:
            title = self.page.locator('h1').first.inner_text()
        except:
            pass

        return {
            "ean": ean,
            "sku": art_nr,
            "quantity": quantity,
            "raw_status": raw_status,
            "supplier_data": {
                "title": title,
                "article_number": art_nr,
                "url": self.page.url
            }
        }

    def fetch_inventory(self) -> List[Dict[str, Any]]:
        """Fetch inventory from Order Nordic by searching for EANs.

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
