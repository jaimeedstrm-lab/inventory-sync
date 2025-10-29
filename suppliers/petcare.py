"""Petcare supplier integration via web scraping."""
import re
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple
from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeout
from suppliers.base import BaseSupplier


class PetcareSupplier(BaseSupplier):
    """Supplier integration for Petcare via web scraping with SKU search."""

    def __init__(self, name: str, config: Dict[str, Any], status_mapping: Dict[str, int], headless: bool = True):
        """Initialize Petcare supplier.

        Args:
            name: Supplier name
            config: Configuration with keys:
                - base_url: Base website URL
                - login_url: Login page URL
                - username: Login username (email)
                - password: Login password
            status_mapping: Status to quantity mapping
            headless: Run browser in headless mode (default True)
        """
        super().__init__(name, config, status_mapping)

        self.base_url = config.get("base_url", "https://www.petcare.se")
        self.login_url = config.get("login_url", "https://www.petcare.se/mitt-konto/")
        self.username = config.get("username")
        self.password = config.get("password")
        self.headless = headless

        self.playwright = None
        self.browser = None
        self.page = None

        # Cookie storage path
        self.cookies_dir = Path("cookies")
        self.cookies_file = self.cookies_dir / "petcare_cookies.json"

    def _save_cookies(self):
        """Save cookies to file for reuse."""
        try:
            # Create cookies directory if it doesn't exist
            self.cookies_dir.mkdir(exist_ok=True)

            # Get cookies from browser context
            cookies = self.page.context.cookies()

            # Save to file
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f, indent=2)

            print(f"  ✓ Cookies saved to {self.cookies_file}")
        except Exception as e:
            print(f"  Warning: Failed to save cookies: {e}")

    def _load_cookies(self) -> bool:
        """Load cookies from file.

        Returns:
            True if cookies loaded successfully, False otherwise
        """
        try:
            if not self.cookies_file.exists():
                print(f"  No saved cookies found")
                return False

            # Load cookies from file
            with open(self.cookies_file, 'r') as f:
                cookies = json.load(f)

            # Add cookies to browser context
            self.page.context.add_cookies(cookies)

            print(f"  ✓ Loaded {len(cookies)} cookies from {self.cookies_file}")
            return True
        except Exception as e:
            print(f"  Warning: Failed to load cookies: {e}")
            return False

    def _verify_logged_in(self) -> bool:
        """Verify if currently logged in.

        Returns:
            True if logged in, False otherwise
        """
        try:
            # Navigate to account page
            self.page.goto(self.login_url, wait_until="domcontentloaded", timeout=15000)
            self.page.wait_for_timeout(2000)

            # Check if we see logout link (indicates logged in)
            # Try multiple selectors for logout link
            logout_selectors = [
                'a:has-text("Logga ut")',
                'a[href*="customer-logout"]',
                'a[href*="wp-login.php?action=logout"]',
                'text="Logga ut"'
            ]

            for selector in logout_selectors:
                try:
                    logout_link = self.page.locator(selector).first
                    if logout_link.is_visible(timeout=2000):
                        print(f"  ✓ Already logged in (found logout link with selector: {selector})")
                        return True
                except:
                    continue

            # Alternative: check if we still see login form (not logged in)
            try:
                login_form = self.page.locator('input[name="username"]').first
                if login_form.is_visible(timeout=2000):
                    print(f"  Not logged in (login form visible)")
                    return False
            except:
                pass

            # If neither found, check the page title or URL
            # If we're on "mitt-konto" and NOT on login page, we're probably logged in
            current_url = self.page.url
            if "mitt-konto" in current_url and "customer-logout" not in current_url:
                # Check if there's account content (not login form)
                try:
                    account_content = self.page.locator('.woocommerce-MyAccount-navigation, .woocommerce-MyAccount-content').first
                    if account_content.is_visible(timeout=2000):
                        print(f"  ✓ Already logged in (found account content)")
                        return True
                except:
                    pass

            print(f"  Could not determine login status - assuming not logged in")
            return False
        except Exception as e:
            print(f"  Error verifying login status: {e}")
            return False

    def authenticate(self) -> bool:
        """Authenticate with Petcare website using cookies or login.

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
            self.page.set_default_timeout(60000)  # 60 seconds for reCAPTCHA

            # Try to load existing cookies first
            print(f"  Attempting to reuse existing session...")
            cookies_loaded = self._load_cookies()

            if cookies_loaded:
                # Verify cookies still work
                if self._verify_logged_in():
                    print(f"  ✓ Session restored from cookies - no login needed!")
                    self.authenticated = True
                    return True
                else:
                    print(f"  Cookies expired or invalid - need to login")

            # Need to login
            print(f"  Navigating to {self.login_url}...")
            self.page.goto(self.login_url, wait_until="domcontentloaded")

            # Wait a bit for page to fully load
            self.page.wait_for_timeout(2000)

            # Wait for login form to be visible
            print(f"  Waiting for login form...")
            self.page.wait_for_selector('input[name="username"]', state="visible", timeout=10000)

            # Fill in credentials
            print(f"  Entering credentials...")

            # Fill username (email)
            username_field = self.page.locator('input[name="username"]').first
            username_field.fill(self.username)
            print(f"    ✓ Username filled")

            # Fill password
            password_field = self.page.locator('input[name="password"]').first
            password_field.fill(self.password)
            print(f"    ✓ Password filled")

            # Check for reCAPTCHA and wait for submit button to be enabled
            print(f"  Checking for reCAPTCHA...")
            submit_button = self.page.locator('button[type="submit"], button:has-text("Logga in")').first

            # Check if button is disabled (indicates reCAPTCHA)
            button_disabled = submit_button.get_attribute("disabled")

            if button_disabled is not None:
                print(f"  ⚠️  reCAPTCHA detected (submit button is disabled)!")

                if self.headless:
                    print(f"  ✗ Cannot solve reCAPTCHA in headless mode")
                    print(f"  Please run with headless=False or implement reCAPTCHA solver")
                    raise Exception("reCAPTCHA detected - requires manual solving or solver service")
                else:
                    print(f"  Please solve the reCAPTCHA manually...")
                    print(f"  Waiting up to 120 seconds for submit button to become enabled...")

                    # Wait for submit button to become enabled (reCAPTCHA solved)
                    try:
                        # Wait for the button to no longer have the disabled attribute
                        submit_button.wait_for(state="attached", timeout=120000)
                        # Use JavaScript to wait for button to be enabled
                        self.page.wait_for_function(
                            """
                            () => {
                                const btn = document.querySelector('button[type="submit"], button[name="login"]');
                                return btn && !btn.disabled;
                            }
                            """,
                            timeout=120000
                        )
                        print(f"  ✓ reCAPTCHA solved! Submit button is now enabled")
                    except:
                        raise Exception("Timeout waiting for reCAPTCHA to be solved")
            else:
                print(f"    No reCAPTCHA detected (button is enabled)")

            # Click login submit button
            print(f"  Submitting login form...")
            submit_button.click()

            # Wait for login to complete
            print(f"  Verifying login...")
            try:
                # Wait for page to reload or some indicator of successful login
                self.page.wait_for_timeout(3000)  # Wait 3 seconds for login to process

                # Check if we're logged in by looking for account elements
                # Typically after login, we should see "Logga ut" or user account info
                try:
                    logout_link = self.page.locator('text="Logga ut", a[href*="customer-logout"]').first
                    if logout_link.is_visible(timeout=5000):
                        print(f"  ✓ Login successful (found logout link)")

                        # Save cookies for future use
                        self._save_cookies()

                        self.authenticated = True
                        return True
                except:
                    pass

                # Alternative check: see if we're still on login page (failed login)
                try:
                    login_form_still_visible = self.page.locator('input[name="username"]').is_visible()
                    if login_form_still_visible:
                        # Check for error message
                        error_msg = self.page.locator('.woocommerce-error, .woocommerce-message').first
                        if error_msg.is_visible():
                            error_text = error_msg.inner_text()
                            raise Exception(f"Login failed: {error_text}")
                        raise Exception("Login form still visible - login may have failed")
                except:
                    # Login form not visible anymore - good sign
                    pass

                print(f"  ✓ Login successful")

                # Save cookies for future use
                self._save_cookies()

                self.authenticated = True
                return True

            except Exception as e:
                raise Exception(f"Could not verify successful login: {str(e)}")

        except Exception as e:
            self.cleanup()
            raise Exception(f"Authentication failed: {str(e)}")

    def search_product_by_sku(self, sku: str, expected_ean: str = None) -> Dict[str, Any]:
        """Search for a product by SKU and scrape its data.

        Args:
            sku: SKU code to search for
            expected_ean: Expected EAN for verification (optional)

        Returns:
            Product dictionary with quantity and data, or None if not found
        """
        print(f"  [DEBUG] search_product_by_sku called with SKU: {sku}, EAN: {expected_ean}")
        print(f"  [DEBUG] authenticated: {self.authenticated}, page exists: {self.page is not None}")

        if not self.authenticated or not self.page:
            raise Exception("Not authenticated. Call authenticate() first.")

        try:
            print(f"  [DEBUG] Starting product search...")
            print(f"  [DEBUG] Current URL: {self.page.url}")

            # Reset to homepage to ensure clean state for search
            if not self.page.url.endswith(self.base_url) and "post_type=product" not in self.page.url:
                print(f"  [DEBUG] Navigating back to homepage for clean search state...")
                try:
                    self.page.goto(self.base_url, timeout=15000, wait_until="domcontentloaded")
                    self.page.wait_for_timeout(1000)
                except Exception as e:
                    print(f"  [DEBUG] Warning: Could not navigate to homepage: {e}")

            # Click search icon to open search field
            # <span class="wd-tools-icon"> with search icon
            print(f"  Clicking search icon to reveal search field...")
            try:
                search_icon_selectors = [
                    'span.wd-tools-icon',
                    'a.search-button',
                    '.wd-tools-icon img[src*="search"]',
                    'span:has(img[alt*="search"])',
                    'span:has(img[src*="search"])'
                ]

                search_icon_clicked = False
                for selector in search_icon_selectors:
                    try:
                        search_icon = self.page.locator(selector).first
                        if search_icon.is_visible(timeout=2000):
                            print(f"  ✓ Found search icon with selector: {selector}")
                            search_icon.click()
                            self.page.wait_for_timeout(1000)  # Wait for search field to appear
                            search_icon_clicked = True
                            break
                    except:
                        continue

                if not search_icon_clicked:
                    print(f"  ⚠️  Could not find search icon, trying to access search field directly")
            except Exception as e:
                print(f"  ⚠️  Error clicking search icon: {e}")

            # Find the search input field
            # Common selectors for WooCommerce/WordPress search
            search_box = None

            selectors_to_try = [
                'input[type="search"][name="s"]',
                'input.search-field',
                'input[placeholder*="Sök"]',
                'input[name="s"]',
                '#woocommerce-product-search-field-0'
            ]

            print(f"  [DEBUG] Looking for search box...")
            for selector in selectors_to_try:
                try:
                    print(f"  [DEBUG] Trying selector: {selector}")
                    search_box = self.page.locator(selector).first
                    search_box.wait_for(state="visible", timeout=3000)
                    print(f"  Found search box with selector: {selector}")
                    break
                except Exception as e:
                    print(f"  [DEBUG] Selector {selector} failed: {e}")
                    continue

            if not search_box:
                print(f"  [DEBUG] Could not find search box with any known selector")
                print(f"  [DEBUG] This may indicate the page has changed or search is not available")
                print(f"  [DEBUG] Skipping SKU: {sku}")
                return None  # Return None instead of raising exception to continue with other products

            # Clear and type the SKU
            search_box.click()
            search_box.fill("")  # Clear
            self.page.wait_for_timeout(300)

            # Type SKU
            search_box.type(sku, delay=50)
            print(f"  Typed SKU: {sku}")

            # Wait for search suggestions to appear
            print(f"  Waiting for search suggestions...")
            self.page.wait_for_timeout(2000)  # Wait for autocomplete/suggestions

            # Debug: Check what's on the page
            try:
                page_content = self.page.content()
                if f"SKU: {sku}" in page_content:
                    print(f"  ✓ SKU {sku} found in page content")
                else:
                    print(f"  ⚠️  SKU {sku} NOT found in page content")

                # Check for any suggestions
                all_suggestions = self.page.locator('p.wd-suggestion-sku').all()
                if all_suggestions:
                    print(f"  Found {len(all_suggestions)} suggestions:")
                    for i, sug in enumerate(all_suggestions[:5]):  # Show first 5
                        try:
                            text = sug.inner_text()
                            print(f"    - {text}")
                        except:
                            pass
                else:
                    print(f"  No suggestions with class 'wd-suggestion-sku' found")
            except Exception as e:
                print(f"  Debug error: {e}")

            # Look for SKU in suggestions dropdown
            # Based on your info: <p class="wd-suggestion-sku">SKU: T6906</p>
            try:
                # Find the suggestion with matching SKU
                suggestion_selector = f'p.wd-suggestion-sku:has-text("SKU: {sku}")'
                suggestion = self.page.locator(suggestion_selector).first

                if suggestion.is_visible(timeout=3000):
                    print(f"  ✓ Found product in suggestions with SKU: {sku}")

                    # Click on the product link to go to product page
                    # The link is typically <a class="wd-fill" href="...">
                    # Try to find it near the suggestion
                    suggestion_link = None

                    try:
                        # Try finding the wd-fill link in the same container
                        suggestion_link = suggestion.locator('xpath=ancestor::*').locator('a.wd-fill').first
                        print(f"  [DEBUG] Found link with wd-fill class")
                    except:
                        try:
                            # Fallback to any ancestor link
                            suggestion_link = suggestion.locator('xpath=ancestor::a').first
                            print(f"  [DEBUG] Found ancestor link")
                        except:
                            print(f"  [DEBUG] Could not find link, will try clicking suggestion directly")

                    if suggestion_link:
                        href = suggestion_link.get_attribute('href')
                        print(f"  Navigating to product: {href}")
                        suggestion_link.click()
                    else:
                        # Last resort: click the suggestion itself
                        print(f"  Clicking suggestion element directly")
                        suggestion.click()

                    # Wait for product page to load
                    self.page.wait_for_load_state("domcontentloaded", timeout=15000)
                    self.page.wait_for_timeout(1500)
                    print(f"  ✓ Product page loaded: {self.page.url}")
                else:
                    # If no suggestion found, try submitting search
                    print(f"  No suggestion found, submitting search...")
                    search_box.press("Enter")

                    # Wait for search results page
                    self.page.wait_for_load_state("domcontentloaded", timeout=10000)
                    self.page.wait_for_timeout(1500)

                    # Try to find and click first product result
                    # Look for product links in search results
                    product_link = self.page.locator('a.woocommerce-LoopProduct-link, .product a.woocommerce-loop-product__link').first
                    if product_link.is_visible(timeout=3000):
                        product_link.click()
                        self.page.wait_for_load_state("domcontentloaded", timeout=10000)
                        self.page.wait_for_timeout(1000)
                    else:
                        print(f"  ✗ No search results found for SKU: {sku}")
                        return None

            except PlaywrightTimeout:
                print(f"  ✗ No suggestions or results found for SKU: {sku}")
                return None

            # Scrape and verify product data from the product page
            product_data = self._scrape_product_page(sku, expected_ean)
            return product_data

        except PlaywrightTimeout:
            # Product not found or timeout
            return None
        except Exception as e:
            print(f"  Warning: Error searching for SKU {sku}: {str(e)}")
            return None

    def _scrape_product_page(self, expected_sku: str, expected_ean: str = None) -> Dict[str, Any]:
        """Scrape product data from current product page.

        Args:
            expected_sku: SKU to verify
            expected_ean: EAN to verify (optional)

        Returns:
            Product dictionary
        """
        # Get and verify SKU
        sku = None
        try:
            # Based on your info: <span class="sku">11620</span>
            sku_element = self.page.locator('span.sku').first
            sku = sku_element.inner_text().strip()

            if sku != expected_sku:
                print(f"  Warning: SKU mismatch - expected {expected_sku}, found {sku}")
                # Continue anyway, but log the mismatch
        except Exception as e:
            print(f"  Warning: Could not find SKU on product page: {str(e)}")
            sku = expected_sku  # Use expected SKU as fallback

        # Get and verify EAN
        ean = None
        if expected_ean:
            try:
                # Based on your info: <span>EAN: <span>5705833116205</span></span>
                ean_element = self.page.locator('span:has-text("EAN:") > span').first
                ean = ean_element.inner_text().strip()

                if ean != expected_ean:
                    raise Exception(f"EAN mismatch on product page: expected {expected_ean}, found {ean}")

                print(f"  ✓ EAN verified: {ean}")
            except Exception as e:
                print(f"  Warning: Could not verify EAN: {str(e)}")
                ean = expected_ean  # Use expected EAN
        else:
            # Try to get EAN even if not expected
            try:
                ean_element = self.page.locator('span:has-text("EAN:") > span').first
                ean = ean_element.inner_text().strip()
            except:
                pass

        # Get stock status
        quantity = 0
        raw_status = None

        try:
            # Based on your info:
            # In stock: <p class="stock in-stock wd-style-default">I lager</p>
            # Out of stock: <p class="stock out-of-stock wd-style-default">Ej i lager</p>

            stock_element = self.page.locator('p.stock').first

            if stock_element.is_visible():
                stock_html = stock_element.get_attribute("class")
                stock_text = stock_element.inner_text().strip()
                raw_status = stock_text

                if "in-stock" in stock_html:
                    # In stock
                    # Check if there's a specific quantity mentioned in text
                    qty_match = re.search(r'(\d+)\s*st', stock_text, re.IGNORECASE)
                    if qty_match:
                        quantity = int(qty_match.group(1))
                    else:
                        # Default to mapped quantity for "i lager"
                        quantity = self.normalize_quantity("i lager")

                    print(f"  ✓ Stock status: In stock ({quantity} units)")

                elif "out-of-stock" in stock_html:
                    # Out of stock
                    quantity = 0
                    print(f"  ✓ Stock status: Out of stock")

                else:
                    # Unknown stock status - try to normalize from text
                    quantity = self.normalize_quantity(stock_text)
                    print(f"  ✓ Stock status: {stock_text} (normalized to {quantity})")

        except Exception as e:
            print(f"  Warning: Could not parse stock status: {str(e)}")
            quantity = 0
            raw_status = "Unknown"

        # Get product title
        title = None
        try:
            title_element = self.page.locator('h1.product_title, h1.entry-title').first
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
                "url": self.page.url
            }
        }

    def fetch_inventory(self) -> List[Dict[str, Any]]:
        """Fetch inventory from Petcare by searching for SKUs.

        This method expects to receive SKUs to search for.
        Since we need the SKU list from Shopify, this is handled differently.

        Returns:
            Empty list (actual fetching happens via search_products_by_sku_list)
        """
        # This supplier works differently - we search individual SKUs
        # The main sync logic will call search_product_by_sku for each SKU
        return []

    def search_products_by_sku_list(self, sku_ean_pairs: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
        """Search for multiple products by SKU.

        Args:
            sku_ean_pairs: List of (SKU, EAN) tuples to search for

        Returns:
            List of found products with inventory data
        """
        if not self.authenticated:
            raise Exception("Not authenticated. Call authenticate() first.")

        products = []
        total = len(sku_ean_pairs)

        print(f"  Searching for {total} products...")

        for i, (sku, ean) in enumerate(sku_ean_pairs, 1):
            if i % 10 == 0 or i == total:
                print(f"  Progress: {i}/{total} products searched...")

            # Refresh homepage every 50 products to prevent page state issues
            if i % 50 == 0:
                print(f"  [DEBUG] Refreshing page state after {i} products...")
                try:
                    self.page.goto(self.base_url, timeout=15000, wait_until="domcontentloaded")
                    self.page.wait_for_timeout(2000)
                except Exception as e:
                    print(f"  [DEBUG] Warning: Could not refresh page: {e}")

            product = self.search_product_by_sku(sku, ean)

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
