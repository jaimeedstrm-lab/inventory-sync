"""Logging system for inventory sync."""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


class SyncLogger:
    """Logger for inventory synchronization operations."""

    def __init__(self, log_dir: str = "logs"):
        """Initialize sync logger.

        Args:
            log_dir: Directory to store log files
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Initialize log data structure
        self.log_data = {
            "timestamp": datetime.now().isoformat(),
            "suppliers_processed": [],
            "summary": {
                "total_supplier_products": 0,
                "matched_products": 0,
                "updated_in_shopify": 0,
                "no_change": 0,
                "not_found_in_shopify": 0,
                "duplicate_identifiers": 0,
                "flagged_for_review": 0,
                "errors": 0
            },
            "updates": [],
            "no_changes": [],
            "not_found": [],
            "duplicates": [],
            "flagged": [],
            "errors": []
        }

        # Generate log filename
        timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file = self.log_dir / f"sync_{timestamp_str}.json"

    def log_supplier_start(self, supplier_name: str):
        """Log start of supplier processing.

        Args:
            supplier_name: Name of the supplier being processed
        """
        self.log_data["suppliers_processed"].append(supplier_name)
        print(f"\n{'='*60}")
        print(f"Processing supplier: {supplier_name}")
        print(f"{'='*60}")

    def log_update(
        self,
        ean: Optional[str],
        sku: Optional[str],
        supplier: str,
        old_qty: int,
        new_qty: int,
        shopify_product_id: Optional[str] = None,
        shopify_variant_id: Optional[str] = None
    ):
        """Log successful inventory update.

        Args:
            ean: Product EAN
            sku: Product SKU
            supplier: Supplier name
            old_qty: Previous quantity
            new_qty: New quantity
            shopify_product_id: Shopify product ID
            shopify_variant_id: Shopify variant ID
        """
        update_entry = {
            "ean": ean,
            "sku": sku,
            "supplier": supplier,
            "old_qty": old_qty,
            "new_qty": new_qty,
            "change": new_qty - old_qty,
            "shopify_product_id": shopify_product_id,
            "shopify_variant_id": shopify_variant_id
        }

        if old_qty == new_qty:
            self.log_data["no_changes"].append(update_entry)
            self.log_data["summary"]["no_change"] += 1
        else:
            self.log_data["updates"].append(update_entry)
            self.log_data["summary"]["updated_in_shopify"] += 1

    def log_not_found(self, ean: Optional[str], sku: Optional[str], supplier: str):
        """Log product not found in Shopify.

        Args:
            ean: Product EAN
            sku: Product SKU
            supplier: Supplier name
        """
        self.log_data["not_found"].append({
            "ean": ean,
            "sku": sku,
            "supplier": supplier
        })
        self.log_data["summary"]["not_found_in_shopify"] += 1

    def log_duplicate(self, identifier: str, identifier_type: str, count: int, products: List[Dict]):
        """Log duplicate identifier found.

        Args:
            identifier: The duplicate identifier (EAN or SKU)
            identifier_type: Type of identifier ("EAN" or "SKU")
            count: Number of products with this identifier
            products: List of product information dictionaries
        """
        self.log_data["duplicates"].append({
            "identifier": identifier,
            "type": identifier_type,
            "count": count,
            "products": products
        })
        self.log_data["summary"]["duplicate_identifiers"] += 1

    def log_flagged(
        self,
        ean: Optional[str],
        sku: Optional[str],
        reason: str,
        old_qty: int,
        new_qty: int,
        supplier: str
    ):
        """Log product flagged for review.

        Args:
            ean: Product EAN
            sku: Product SKU
            reason: Reason for flagging
            old_qty: Previous quantity
            new_qty: New quantity
            supplier: Supplier name
        """
        self.log_data["flagged"].append({
            "ean": ean,
            "sku": sku,
            "reason": reason,
            "old_qty": old_qty,
            "new_qty": new_qty,
            "supplier": supplier
        })
        self.log_data["summary"]["flagged_for_review"] += 1

    def log_error(
        self,
        error_type: str,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """Log error.

        Args:
            error_type: Type of error
            message: Error message
            context: Additional context information
        """
        error_entry = {
            "type": error_type,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        if context:
            error_entry["context"] = context

        self.log_data["errors"].append(error_entry)
        self.log_data["summary"]["errors"] += 1

        print(f"❌ ERROR ({error_type}): {message}")

    def increment_supplier_products(self, count: int):
        """Increment total supplier products count.

        Args:
            count: Number of products to add to total
        """
        self.log_data["summary"]["total_supplier_products"] += count

    def increment_matched_products(self, count: int = 1):
        """Increment matched products count.

        Args:
            count: Number of matched products to add
        """
        self.log_data["summary"]["matched_products"] += count

    def print_summary(self):
        """Print summary to console."""
        summary = self.log_data["summary"]
        print(f"\n{'='*60}")
        print("SYNC SUMMARY")
        print(f"{'='*60}")
        print(f"Suppliers processed: {', '.join(self.log_data['suppliers_processed'])}")
        print(f"\nProducts:")
        print(f"  Total from suppliers:     {summary['total_supplier_products']}")
        print(f"  Matched in Shopify:       {summary['matched_products']}")
        print(f"  Updated in Shopify:       {summary['updated_in_shopify']}")
        print(f"  No change needed:         {summary['no_change']}")
        print(f"\nIssues:")
        print(f"  Not found in Shopify:     {summary['not_found_in_shopify']}")
        print(f"  Duplicate identifiers:    {summary['duplicate_identifiers']}")
        print(f"  Flagged for review:       {summary['flagged_for_review']}")
        print(f"  Errors:                   {summary['errors']}")
        print(f"\nLog file: {self.log_file}")
        print(f"{'='*60}\n")

    def save(self):
        """Save log data to JSON file."""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(self.log_data, f, indent=2, ensure_ascii=False)

    def get_summary(self) -> Dict[str, Any]:
        """Get summary data.

        Returns:
            Dictionary containing summary statistics
        """
        return self.log_data["summary"]

    def has_warnings(self) -> bool:
        """Check if there are any warnings (not found, flagged, duplicates).

        Returns:
            True if there are warnings
        """
        summary = self.log_data["summary"]
        return (
            summary["not_found_in_shopify"] > 0 or
            summary["flagged_for_review"] > 0 or
            summary["duplicate_identifiers"] > 0
        )

    def has_errors(self) -> bool:
        """Check if there are any errors.

        Returns:
            True if there are errors
        """
        return self.log_data["summary"]["errors"] > 0

    def get_not_found_products(self) -> List[Dict[str, Any]]:
        """Get list of products not found in Shopify.

        Returns:
            List of not found product dictionaries
        """
        return self.log_data["not_found"]

    def get_flagged_products(self) -> List[Dict[str, Any]]:
        """Get list of products flagged for review.

        Returns:
            List of flagged product dictionaries
        """
        return self.log_data["flagged"]

    def get_errors(self) -> List[Dict[str, Any]]:
        """Get list of errors.

        Returns:
            List of error dictionaries
        """
        return self.log_data["errors"]
