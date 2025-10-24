"""Product matching logic for inventory synchronization."""
from typing import Dict, List, Optional, Tuple, Any
from utils.helpers import normalize_ean, normalize_sku


class InventoryMatcher:
    """Match supplier products with Shopify products."""

    def __init__(self, shopify_variants: Dict[str, Dict[str, Any]]):
        """Initialize matcher with Shopify product data.

        Args:
            shopify_variants: Dictionary mapping identifiers to variant data
                Format: {"EAN:1234567890": {...}, "SKU:ABC-123": {...}}
        """
        self.shopify_variants = shopify_variants

        # Build reverse lookup for duplicate detection
        self.ean_lookup = {}
        self.sku_lookup = {}

        for key, variant in shopify_variants.items():
            if key.startswith("EAN:"):
                ean = key[4:]  # Remove "EAN:" prefix
                if ean not in self.ean_lookup:
                    self.ean_lookup[ean] = []
                self.ean_lookup[ean].append(variant)

            elif key.startswith("SKU:"):
                sku = key[4:]  # Remove "SKU:" prefix
                if sku not in self.sku_lookup:
                    self.sku_lookup[sku] = []
                self.sku_lookup[sku].append(variant)

    def match_product(
        self,
        ean: Optional[str],
        sku: Optional[str]
    ) -> Tuple[Optional[Dict[str, Any]], str, Optional[str]]:
        """Match a supplier product to a Shopify variant.

        Matching priority:
        1. Try EAN first (if provided)
        2. Fall back to SKU (if EAN not found or not provided)

        Args:
            ean: Product EAN/barcode
            sku: Product SKU

        Returns:
            Tuple of (variant_data, match_type, error_message):
            - variant_data: Matched Shopify variant dict or None
            - match_type: "ean", "sku", "duplicate", or "not_found"
            - error_message: Error description if applicable
        """
        # Normalize identifiers
        normalized_ean = normalize_ean(ean)
        normalized_sku = normalize_sku(sku)

        # Try EAN match first (priority)
        if normalized_ean:
            ean_key = f"EAN:{normalized_ean}"
            if ean_key in self.shopify_variants:
                # Check for duplicates
                if len(self.ean_lookup.get(normalized_ean, [])) > 1:
                    return (
                        None,
                        "duplicate",
                        f"Multiple products found with EAN: {normalized_ean}"
                    )
                return self.shopify_variants[ean_key], "ean", None

        # Fall back to SKU match
        if normalized_sku:
            sku_key = f"SKU:{normalized_sku}"
            if sku_key in self.shopify_variants:
                # Check for duplicates
                if len(self.sku_lookup.get(normalized_sku, [])) > 1:
                    return (
                        None,
                        "duplicate",
                        f"Multiple products found with SKU: {normalized_sku}"
                    )
                return self.shopify_variants[sku_key], "sku", None

        # No match found
        return None, "not_found", f"No match found for EAN: {normalized_ean}, SKU: {normalized_sku}"

    def match_products_batch(
        self,
        supplier_products: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Match a batch of supplier products.

        Args:
            supplier_products: List of supplier product dictionaries with keys:
                - ean: str (optional)
                - sku: str (optional)
                - quantity: int
                - ... (other supplier-specific fields)

        Returns:
            Dictionary with match results:
            {
                "matched": [
                    {
                        "supplier_product": {...},
                        "shopify_variant": {...},
                        "match_type": "ean" or "sku"
                    }
                ],
                "not_found": [
                    {
                        "supplier_product": {...},
                        "error": "..."
                    }
                ],
                "duplicates": [
                    {
                        "supplier_product": {...},
                        "error": "..."
                    }
                ]
            }
        """
        results = {
            "matched": [],
            "not_found": [],
            "duplicates": []
        }

        for product in supplier_products:
            ean = product.get("ean")
            sku = product.get("sku")

            variant, match_type, error = self.match_product(ean, sku)

            if match_type == "duplicate":
                results["duplicates"].append({
                    "supplier_product": product,
                    "error": error
                })
            elif match_type == "not_found":
                results["not_found"].append({
                    "supplier_product": product,
                    "error": error
                })
            else:
                results["matched"].append({
                    "supplier_product": product,
                    "shopify_variant": variant,
                    "match_type": match_type
                })

        return results

    def get_duplicate_identifiers(self) -> List[Dict[str, Any]]:
        """Get list of duplicate identifiers in Shopify.

        Returns:
            List of duplicate entries:
            [
                {
                    "identifier": "1234567890",
                    "type": "EAN",
                    "count": 3,
                    "products": [...]
                }
            ]
        """
        duplicates = []

        # Check EAN duplicates
        for ean, variants in self.ean_lookup.items():
            if len(variants) > 1:
                duplicates.append({
                    "identifier": ean,
                    "type": "EAN",
                    "count": len(variants),
                    "products": [
                        {
                            "product_id": v["product_id"],
                            "variant_id": v["variant_id"],
                            "title": v["title"],
                            "sku": v["sku"]
                        }
                        for v in variants
                    ]
                })

        # Check SKU duplicates
        for sku, variants in self.sku_lookup.items():
            if len(variants) > 1:
                duplicates.append({
                    "identifier": sku,
                    "type": "SKU",
                    "count": len(variants),
                    "products": [
                        {
                            "product_id": v["product_id"],
                            "variant_id": v["variant_id"],
                            "title": v["title"],
                            "ean": v["barcode"]
                        }
                        for v in variants
                    ]
                })

        return duplicates

    def get_stats(self) -> Dict[str, int]:
        """Get statistics about the Shopify product catalog.

        Returns:
            Dictionary with statistics
        """
        total_variants = len(self.shopify_variants)
        ean_count = len([k for k in self.shopify_variants.keys() if k.startswith("EAN:")])
        sku_count = len([k for k in self.shopify_variants.keys() if k.startswith("SKU:")])
        ean_duplicates = len([ean for ean, variants in self.ean_lookup.items() if len(variants) > 1])
        sku_duplicates = len([sku for sku, variants in self.sku_lookup.items() if len(variants) > 1])

        return {
            "total_variant_identifiers": total_variants,
            "products_with_ean": ean_count,
            "products_with_sku": sku_count,
            "duplicate_eans": ean_duplicates,
            "duplicate_skus": sku_duplicates
        }
