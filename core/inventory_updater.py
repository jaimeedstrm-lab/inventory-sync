"""Inventory update logic with safety checks."""
from typing import Dict, List, Any, Optional
from utils.helpers import calculate_quantity_drop_percent


class InventoryUpdater:
    """Handle inventory updates with safety checks."""

    def __init__(
        self,
        max_quantity_drop_percent: int = 80,
        min_quantity_for_zero_check: int = 50,
        enable_safety_checks: bool = True
    ):
        """Initialize inventory updater.

        Args:
            max_quantity_drop_percent: Maximum allowed percentage drop in quantity
            min_quantity_for_zero_check: Minimum quantity to flag when going to zero
            enable_safety_checks: Whether to enable safety checks
        """
        self.max_quantity_drop_percent = max_quantity_drop_percent
        self.min_quantity_for_zero_check = min_quantity_for_zero_check
        self.enable_safety_checks = enable_safety_checks

    def should_flag_update(
        self,
        old_qty: int,
        new_qty: int
    ) -> Optional[str]:
        """Check if update should be flagged for review.

        Args:
            old_qty: Current quantity in Shopify
            new_qty: New quantity from supplier

        Returns:
            Reason for flagging, or None if update is safe
        """
        if not self.enable_safety_checks:
            return None

        # Flag if high-quantity item goes to zero
        if old_qty >= self.min_quantity_for_zero_check and new_qty == 0:
            return f"high_quantity_to_zero (was {old_qty}, now 0)"

        # Skip percentage check if going to zero (items sold out are expected)
        if new_qty == 0:
            return None

        # Flag if quantity drops by more than threshold percentage (but not to zero)
        drop_percent = calculate_quantity_drop_percent(old_qty, new_qty)
        if drop_percent >= self.max_quantity_drop_percent:
            return f"quantity_drop_{int(drop_percent)}% (was {old_qty}, now {new_qty})"

        return None

    def process_updates(
        self,
        matched_products: List[Dict[str, Any]],
        supplier_name: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Process matched products and categorize updates.

        Args:
            matched_products: List of matched product dictionaries from InventoryMatcher
                Format: [{"supplier_product": {...}, "shopify_variant": {...}, "match_type": "ean"}]
            supplier_name: Name of the supplier

        Returns:
            Dictionary with categorized updates:
            {
                "safe_updates": [
                    {
                        "inventory_item_id": int,
                        "old_quantity": int,
                        "new_quantity": int,
                        "ean": str,
                        "sku": str,
                        "supplier": str,
                        "product_id": int,
                        "variant_id": int
                    }
                ],
                "flagged_updates": [
                    {
                        ... (same as above) ...,
                        "flag_reason": str
                    }
                ],
                "no_change": [...]
            }
        """
        results = {
            "safe_updates": [],
            "flagged_updates": [],
            "no_change": []
        }

        for match in matched_products:
            supplier_product = match["supplier_product"]
            shopify_variant = match["shopify_variant"]

            old_qty = shopify_variant["inventory_quantity"]
            new_qty = supplier_product["quantity"]

            update_data = {
                "inventory_item_id": shopify_variant["inventory_item_id"],
                "old_quantity": old_qty,
                "new_quantity": new_qty,
                "ean": supplier_product.get("ean"),
                "sku": supplier_product.get("sku"),
                "supplier": supplier_name,
                "product_id": shopify_variant["product_id"],
                "variant_id": shopify_variant["variant_id"],
                "shopify_title": shopify_variant["title"]
            }

            # Check if quantity changed
            if old_qty == new_qty:
                results["no_change"].append(update_data)
                continue

            # Check for safety flags
            flag_reason = self.should_flag_update(old_qty, new_qty)

            if flag_reason:
                update_data["flag_reason"] = flag_reason
                results["flagged_updates"].append(update_data)
            else:
                results["safe_updates"].append(update_data)

        return results

    def prepare_shopify_updates(
        self,
        safe_updates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Prepare update data for Shopify batch update.

        Args:
            safe_updates: List of safe update dictionaries

        Returns:
            List of update dictionaries formatted for ShopifyClient.batch_update_inventory
        """
        return [
            {
                "inventory_item_id": update["inventory_item_id"],
                "quantity": update["new_quantity"],
                "sku": update["sku"],
                "ean": update["ean"]
            }
            for update in safe_updates
        ]

    def get_summary(
        self,
        safe_updates: List[Dict[str, Any]],
        flagged_updates: List[Dict[str, Any]],
        no_change: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Get summary of update categorization.

        Args:
            safe_updates: List of safe updates
            flagged_updates: List of flagged updates
            no_change: List of unchanged products

        Returns:
            Summary dictionary
        """
        total_increases = sum(1 for u in safe_updates if u["new_quantity"] > u["old_quantity"])
        total_decreases = sum(1 for u in safe_updates if u["new_quantity"] < u["old_quantity"])

        return {
            "total_matched": len(safe_updates) + len(flagged_updates) + len(no_change),
            "safe_updates": len(safe_updates),
            "flagged_updates": len(flagged_updates),
            "no_change": len(no_change),
            "quantity_increases": total_increases,
            "quantity_decreases": total_decreases
        }

    def format_flagged_report(self, flagged_updates: List[Dict[str, Any]]) -> str:
        """Format flagged updates into a readable report.

        Args:
            flagged_updates: List of flagged update dictionaries

        Returns:
            Formatted report string
        """
        if not flagged_updates:
            return "No updates flagged for review."

        report = f"\n{'='*60}\n"
        report += f"FLAGGED UPDATES ({len(flagged_updates)} items)\n"
        report += f"{'='*60}\n\n"

        for update in flagged_updates:
            report += f"Product: {update['shopify_title']}\n"
            report += f"  EAN: {update['ean']} / SKU: {update['sku']}\n"
            report += f"  Supplier: {update['supplier']}\n"
            report += f"  Change: {update['old_quantity']} → {update['new_quantity']}\n"
            report += f"  Reason: {update['flag_reason']}\n"
            report += f"  Product ID: {update['product_id']} / Variant ID: {update['variant_id']}\n"
            report += "\n"

        return report
