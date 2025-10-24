"""Base supplier class for inventory integrations."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from utils.helpers import normalize_status


class BaseSupplier(ABC):
    """Abstract base class for supplier integrations."""

    def __init__(self, name: str, config: Dict[str, Any], status_mapping: Dict[str, int]):
        """Initialize supplier.

        Args:
            name: Supplier name
            config: Supplier-specific configuration
            status_mapping: Dictionary mapping status strings to quantities
        """
        self.name = name
        self.config = config
        self.status_mapping = status_mapping
        self.authenticated = False

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the supplier system.

        Returns:
            True if authentication successful, False otherwise

        Raises:
            Exception: If authentication fails
        """
        pass

    @abstractmethod
    def fetch_inventory(self) -> List[Dict[str, Any]]:
        """Fetch inventory data from supplier.

        Returns:
            List of product dictionaries with standardized format:
            [
                {
                    "ean": "1234567890123",  # Optional
                    "sku": "ABC-123",         # Optional
                    "quantity": 10,           # Required
                    "raw_status": "In Stock", # Optional - original status
                    "supplier_data": {...}    # Optional - any additional data
                },
                ...
            ]

        Raises:
            Exception: If fetching fails
        """
        pass

    def normalize_quantity(self, raw_status: Any) -> int:
        """Normalize status to quantity using configured mapping.

        Args:
            raw_status: Raw status value from supplier

        Returns:
            Normalized quantity as integer
        """
        return normalize_status(raw_status, self.status_mapping)

    def get_products(self) -> List[Dict[str, Any]]:
        """Get products with normalized inventory.

        This is the main method to be called by the sync system.
        It handles authentication and fetching, returning standardized data.

        Returns:
            List of product dictionaries with normalized quantities

        Raises:
            Exception: If authentication or fetching fails
        """
        if not self.authenticated:
            print(f"Authenticating with {self.name}...")
            if not self.authenticate():
                raise Exception(f"Failed to authenticate with {self.name}")
            print(f"✓ Authentication successful")

        print(f"Fetching inventory from {self.name}...")
        products = self.fetch_inventory()
        print(f"✓ Fetched {len(products)} products from {self.name}")

        return products

    def validate_product_data(self, product: Dict[str, Any]) -> bool:
        """Validate that product data has required fields.

        Args:
            product: Product dictionary

        Returns:
            True if valid, False otherwise
        """
        # Must have at least one identifier (EAN or SKU)
        has_identifier = product.get("ean") or product.get("sku")

        # Must have quantity
        has_quantity = "quantity" in product and isinstance(product["quantity"], (int, float))

        return has_identifier and has_quantity

    def cleanup(self):
        """Cleanup resources (close sessions, etc.).

        Override this method if your supplier needs cleanup.
        """
        pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
