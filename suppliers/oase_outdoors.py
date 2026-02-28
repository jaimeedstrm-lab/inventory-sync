"""Oase Outdoors supplier integration via dealer portal and API."""
import requests
from typing import List, Dict, Any
from suppliers.base import BaseSupplier


class OaseOutdoorsSupplier(BaseSupplier):
    """Supplier integration for Oase Outdoors via dealer portal API."""

    def __init__(self, name: str, config: Dict[str, Any], status_mapping: Dict[str, int]):
        """Initialize Oase Outdoors supplier.

        Args:
            name: Supplier name
            config: Configuration with keys:
                - portal_url: Dealer portal URL
                - api_url: API endpoint URL
                - username: Login email
                - password: Login password
            status_mapping: Status to quantity mapping
        """
        super().__init__(name, config, status_mapping)

        self.base_url = config.get("base_url", "https://dealernet.oase-outdoors.dk")
        self.portal_url = config.get("portal_url", "https://dealernet.oase-outdoors.dk/en-gb/login")
        self.api_url = config.get("api_url", "https://dealernet.oase-outdoors.dk/api/dealernet/order/items/en-GB/dealernet-order")
        self.username = config.get("username")
        self.password = config.get("password")

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def authenticate(self) -> bool:
        """Authenticate with Oase Outdoors dealer portal.

        Returns:
            True if authentication successful

        Raises:
            Exception: If authentication fails
        """
        try:
            # Step 1: Get the login page to establish session and get cookies
            print(f"  Accessing dealer portal...")
            response = self.session.get(self.portal_url, timeout=30)

            if response.status_code != 200:
                raise Exception(f"Failed to access portal: HTTP {response.status_code}")

            # Step 2: Submit login form
            print(f"  Submitting login form...")

            login_data = {
                "ID": "5827",
                "DWExtranetUsernameRemember": "True",
                "DWExtranetPasswordRemember": "True",
                "GoBackToPage": "",
                "LoginAction": "Login",
                "redirect": "/en-gb/home",
                "username": self.username,
                "password": self.password,
            }

            response = self.session.post(
                self.portal_url,
                data=login_data,
                allow_redirects=True,
                timeout=30
            )

            if response.status_code != 200:
                raise Exception(f"Login POST failed: HTTP {response.status_code}")

            # Step 3: Verify login by checking for the Dynamicweb.Extranet session cookie
            print(f"  Verifying login...")
            if "Dynamicweb.Extranet" in self.session.cookies:
                print(f"  ✓ Login successful")
            else:
                raise Exception("Login verification failed - session cookie not set after login")

            # Step 4: Verify API access
            test_response = self.session.get(self.api_url, timeout=30)

            if test_response.status_code == 200:
                try:
                    data = test_response.json()
                    if data and 'Products' in data:
                        self.authenticated = True
                        print(f"  ✓ API access confirmed")
                        return True
                except Exception:
                    pass

            raise Exception(
                f"Could not access API after login. "
                f"Status: {test_response.status_code}. "
                f"Please verify credentials are correct."
            )

        except Exception as e:
            raise Exception(f"Authentication failed: {str(e)}")

    def fetch_inventory(self) -> List[Dict[str, Any]]:
        """Fetch inventory from Oase Outdoors API.

        Returns:
            List of product dictionaries

        Raises:
            Exception: If fetch fails
        """
        if not self.authenticated:
            raise Exception("Not authenticated. Call authenticate() first.")

        products = []

        try:
            print(f"  Fetching inventory from API...")

            # Fetch all products (API might support pagination)
            # Start with a large page size, adjust if needed
            params = {
                "PageSize": 10000,  # Try to get all products at once
                "Page": 1
            }

            response = self.session.get(
                self.api_url,
                params=params,
                timeout=60
            )

            response.raise_for_status()
            data = response.json()

            # Parse response - new Oase API returns {"Products": [...], ...}
            items = []

            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get('Products') or data.get('Items') or data.get('items') or []

            print(f"  Received {len(items)} items from API")

            # Parse each item
            for item in items:
                product = self._parse_product(item)
                if product and self.validate_product_data(product):
                    products.append(product)

            print(f"  Parsed {len(products)} valid products")

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch inventory: {str(e)}")

        return products

    def _parse_product(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a single product from Oase API response.

        Args:
            item: Raw product data from API

        Returns:
            Standardized product dictionary
        """
        # Extract EAN - new API uses "Ean" key
        ean = (
            item.get("Ean") or
            item.get("EAN") or
            item.get("ean") or
            item.get("Barcode") or
            item.get("barcode")
        )

        # Extract SKU/Product Number
        sku = (
            item.get("ItemNumber") or  # Oase uses ItemNumber
            item.get("ItemID") or
            item.get("ItemId") or
            item.get("ProductNumber") or
            item.get("ProductNo") or
            item.get("SKU") or
            item.get("sku") or
            item.get("Number")
        )

        # Extract quantity - Oase uses AvailabilityQty
        quantity = (
            item.get("AvailabilityQty") or
            item.get("Stock") or
            item.get("StockLevel") or
            item.get("Quantity") or
            item.get("InStock")
        )

        # Try to convert to integer
        if quantity is not None:
            try:
                quantity = int(float(quantity))
                # Clamp negative values to 0 (Oase returns negative for some out-of-stock items)
                if quantity < 0:
                    quantity = 0
            except (ValueError, TypeError):
                # If not numeric, try to normalize status string
                quantity = self.normalize_quantity(quantity)
        else:
            quantity = 0

        # Build standardized product dict
        product = {
            "ean": str(ean).strip() if ean else None,
            "sku": str(sku).strip() if sku else None,
            "quantity": quantity,
            "supplier_data": {
                "item_number": item.get("ItemNumber"),
                "product_name": item.get("ProductName") or item.get("ProductnameBrand") or item.get("Name"),
                "brand": item.get("Brand"),
                "price": item.get("Price"),
                "sold_out": item.get("Soldout"),
                "availability": item.get("Availability"),
                "raw_item": item
            }
        }

        return product

    def cleanup(self):
        """Close session."""
        if self.session:
            self.session.close()
