"""Shopify API client with rate limiting and retry logic."""
import time
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
from utils.helpers import safe_int


class ShopifyClient:
    """Client for interacting with Shopify Admin API."""

    def __init__(self, shop_url: str, access_token: str, api_version: str = "2024-10"):
        """Initialize Shopify client.

        Args:
            shop_url: Shopify store URL (e.g., "your-store.myshopify.com")
            access_token: Shopify Admin API access token
            api_version: API version to use
        """
        self.shop_url = shop_url.replace('https://', '').replace('http://', '')
        self.access_token = access_token
        self.api_version = api_version
        self.base_url = f"https://{self.shop_url}/admin/api/{api_version}"

        # Rate limiting configuration
        self.requests_per_second = 2  # Shopify Basic plan limit
        self.max_retries = 10  # Increased for rate limiting scenarios
        self.retry_delay = 2  # seconds
        self.last_request_time = 0

    def _wait_for_rate_limit(self):
        """Wait if necessary to respect rate limits."""
        time_since_last_request = time.time() - self.last_request_time
        min_interval = 1.0 / self.requests_per_second

        if time_since_last_request < min_interval:
            time.sleep(min_interval - time_since_last_request)

        self.last_request_time = time.time()

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to Shopify API with retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, etc.)
            endpoint: API endpoint (without base URL)
            data: Request body data
            params: URL parameters

        Returns:
            Response JSON data

        Raises:
            requests.exceptions.RequestException: If request fails after retries
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json"
        }

        for attempt in range(self.max_retries):
            try:
                self._wait_for_rate_limit()

                # Separate loop for handling rate limiting (don't count as retries)
                max_rate_limit_attempts = 20  # Allow up to 20 rate limit waits
                for rate_limit_attempt in range(max_rate_limit_attempts):
                    response = requests.request(
                        method=method,
                        url=url,
                        headers=headers,
                        json=data,
                        params=params,
                        timeout=30
                    )

                    # Handle rate limiting (429 Too Many Requests)
                    if response.status_code == 429:
                        retry_after = safe_int(response.headers.get('Retry-After', self.retry_delay), default=self.retry_delay)
                        print(f"Rate limited. Waiting {retry_after} seconds...")
                        time.sleep(retry_after)
                        continue  # Try again without counting as failed attempt

                    # Success or other error - break out of rate limit loop
                    break
                else:
                    # Exhausted rate limit attempts
                    raise requests.exceptions.RequestException(f"Rate limited too many times ({max_rate_limit_attempts} attempts)")

                # Raise exception for other HTTP errors (but not 429 since we handled it above)
                response.raise_for_status()

                return response.json() if response.content else {}

            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    print(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise

        raise requests.exceptions.RequestException(f"Failed after {self.max_retries} retries")

    def get_all_products(self, tags: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch all products with variants from Shopify.

        Args:
            tags: Optional comma-separated list of tags to filter by (e.g., "supplier:order_nordic")

        Returns:
            List of product dictionaries with variants

        Note:
            This uses cursor-based pagination (Link header) to fetch all products.
        """
        all_products = []
        url = f"{self.base_url}/products.json"
        params = {"limit": 250}  # Maximum allowed per page

        if tags:
            params["tags"] = tags
            print(f"Fetching products from Shopify with tags: {tags}...")
        else:
            print("Fetching products from Shopify...")

        while url:
            # Make request manually to access headers
            headers = {
                "X-Shopify-Access-Token": self.access_token,
                "Content-Type": "application/json"
            }

            self._wait_for_rate_limit()

            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                response.raise_for_status()

                data = response.json()
                products = data.get("products", [])

                if not products:
                    break

                all_products.extend(products)
                print(f"Fetched {len(all_products)} products so far...")

                # Get next page URL from Link header
                link_header = response.headers.get("Link", "")
                url = None  # Reset URL
                # NOTE: Don't clear params here - pagination URLs include all params

                # Parse Link header for next page
                # Format: <https://...>; rel="next", <https://...>; rel="previous"
                if link_header:
                    for link in link_header.split(","):
                        if 'rel="next"' in link:
                            # Extract URL from <URL>
                            url = link.split(";")[0].strip().strip("<>")
                            params = {}  # Clear params when using full URL from pagination
                            break

            except requests.exceptions.RequestException as e:
                print(f"Error fetching products: {e}")
                break

        print(f"Total products fetched: {len(all_products)}")
        return all_products

    def get_product_variants_with_inventory(self, tags: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Get all product variants with their inventory information.

        Args:
            tags: Optional comma-separated list of tags to filter by (e.g., "supplier:order_nordic")
                  Filtering is done client-side for reliability.

        Returns:
            Dictionary mapping identifiers (EAN/SKU) to variant data:
            {
                "EAN:1234567890": {
                    "product_id": 123,
                    "variant_id": 456,
                    "inventory_item_id": 789,
                    "sku": "ABC-123",
                    "barcode": "1234567890",
                    "title": "Product Title - Variant Title",
                    "inventory_quantity": 10
                },
                "SKU:ABC-123": { ... }
            }
        """
        # Fetch all products (without server-side filtering)
        all_products = self.get_all_products(tags=None)

        # Filter client-side if tags specified
        if tags:
            filter_tags = [t.strip() for t in tags.split(',')]
            filtered_products = []

            for product in all_products:
                product_tags_str = product.get('tags', '')
                if product_tags_str:
                    product_tags = [t.strip() for t in product_tags_str.split(',')]
                    # Check if any of the filter tags match
                    if any(filter_tag in product_tags for filter_tag in filter_tags):
                        filtered_products.append(product)

            print(f"  Client-side filtered: {len(all_products)} -> {len(filtered_products)} products")
            products = filtered_products
        else:
            products = all_products

        variant_map = {}

        # Get primary location ID for inventory updates
        primary_location_id = self.get_primary_location_id()

        for product in products:
            product_tags = product.get("tags", "")
            for variant in product.get("variants", []):
                variant_data = {
                    "product_id": product["id"],
                    "variant_id": variant["id"],
                    "inventory_item_id": variant.get("inventory_item_id"),
                    "location_id": primary_location_id,
                    "sku": variant.get("sku"),
                    "barcode": variant.get("barcode"),
                    "title": f"{product['title']} - {variant['title']}",
                    "product_title": product.get("title"),
                    "variant_title": variant.get("title"),
                    "inventory_quantity": safe_int(variant.get("inventory_quantity"), default=0),
                    "product_tags": product_tags
                }

                # Map by EAN/barcode
                if variant.get("barcode"):
                    ean_key = f"EAN:{variant['barcode']}"
                    variant_map[ean_key] = variant_data

                # Map by SKU
                if variant.get("sku"):
                    sku_key = f"SKU:{variant['sku']}"
                    variant_map[sku_key] = variant_data

        print(f"Mapped {len(variant_map)} variant identifiers (EAN/SKU)")
        return variant_map

    def update_inventory_level(
        self,
        inventory_item_id: int,
        location_id: int,
        available: int
    ) -> Dict[str, Any]:
        """Update inventory level for a specific item at a location.

        Args:
            inventory_item_id: Shopify inventory item ID
            location_id: Shopify location ID
            available: New available quantity

        Returns:
            Response data from Shopify

        Note:
            Uses the inventory_levels/set.json endpoint
        """
        # Ensure all values are proper integers (handle edge cases where they might be strings/floats)
        data = {
            "inventory_item_id": safe_int(inventory_item_id),
            "location_id": safe_int(location_id),
            "available": safe_int(available)
        }

        return self._make_request("POST", "inventory_levels/set.json", data=data)

    def get_locations(self) -> List[Dict[str, Any]]:
        """Get all locations for the store.

        Returns:
            List of location dictionaries
        """
        response = self._make_request("GET", "locations.json")
        return response.get("locations", [])

    def get_primary_location_id(self) -> Optional[int]:
        """Get the primary location ID for inventory updates.

        Returns:
            Primary location ID or None if no locations found
        """
        locations = self.get_locations()

        if not locations:
            return None

        # Try to find active primary location
        for location in locations:
            if location.get("active") and location.get("legacy"):
                return location["id"]

        # Fallback to first active location
        for location in locations:
            if location.get("active"):
                return location["id"]

        # Last resort: first location
        return locations[0]["id"] if locations else None

    def batch_update_inventory(
        self,
        updates: List[Dict[str, Any]],
        location_id: Optional[int] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Update inventory for multiple items.

        Args:
            updates: List of update dictionaries with keys:
                - inventory_item_id: int
                - quantity: int
                - sku: str (for logging)
                - ean: str (for logging)
            location_id: Location ID (if None, uses primary location)
            dry_run: If True, don't actually update, just simulate

        Returns:
            Dictionary with results:
            {
                "total": int,
                "successful": int,
                "failed": int,
                "skipped": int (dry run),
                "errors": [...]
            }
        """
        if location_id is None:
            location_id = self.get_primary_location_id()
            if location_id is None:
                raise ValueError("No location found for inventory updates")

        results = {
            "total": len(updates),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }

        print(f"\n{'Simulating' if dry_run else 'Updating'} inventory for {len(updates)} items...")

        for update in updates:
            inventory_item_id = update["inventory_item_id"]
            quantity = update["quantity"]
            sku = update.get("sku", "N/A")
            ean = update.get("ean", "N/A")

            try:
                if dry_run:
                    print(f"  [DRY RUN] Would update {sku} (EAN: {ean}) to quantity: {quantity}")
                    results["skipped"] += 1
                else:
                    self.update_inventory_level(
                        inventory_item_id=inventory_item_id,
                        location_id=location_id,
                        available=quantity
                    )
                    print(f"  ✓ Updated {sku} (EAN: {ean}) to quantity: {quantity}")
                    results["successful"] += 1

            except Exception as e:
                error_msg = f"Failed to update {sku} (EAN: {ean}): {str(e)}"
                print(f"  ✗ {error_msg}")
                results["failed"] += 1
                results["errors"].append({
                    "sku": sku,
                    "ean": ean,
                    "error": str(e)
                })

        return results

    def test_connection(self) -> bool:
        """Test connection to Shopify API.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = self._make_request("GET", "shop.json")
            shop_name = response.get("shop", {}).get("name", "Unknown")
            print(f"✓ Successfully connected to Shopify store: {shop_name}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect to Shopify: {e}")
            return False
